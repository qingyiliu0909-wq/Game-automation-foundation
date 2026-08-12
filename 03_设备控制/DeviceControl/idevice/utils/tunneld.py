from __future__ import annotations

import logging
import os
import shlex
import shutil
import signal
import subprocess
import sys
import threading
import time
from typing import List, Mapping, NamedTuple, Tuple, Optional
import traceback
import fastapi
import uvicorn
from fastapi import FastAPI, Response
from packaging.version import Version, InvalidVersion
from pymobiledevice3.exceptions import MuxException
from pymobiledevice3.osu.os_utils import OsUtils

from DeviceControl.idevice.api import list_devices

logger = logging.getLogger(__name__)
os_utils = OsUtils.create()


class Address(NamedTuple):
    ip: str
    port: int


def is_valid_version(ver_str, min_ver_str):
    try:
        return Version(ver_str) >= Version(min_ver_str)
    except InvalidVersion:
        return False

def get_connected_devices() -> list[str]:
    try:
        devices = list_devices(usb=True, network=False)
    except MuxException as e:
        logger.error("list_devices failed: %s", e)
        return []
    return [
        d["udid"]
        for d in devices
        if "product_version" in d and is_valid_version(d["product_version"], "17.0")
    ]


def get_need_lockdown_devices() -> list[str]:
    try:
        devices = list_devices(usb=True, network=False)
    except MuxException as e:
        logger.error("list_devices failed: %s", e)
        return []
    return [
        d["udid"]
        for d in devices
        if Version(d.get("product_version", "0")) >= Version("17.0")
    ]



def guess_pymobiledevice3_cmd() -> List[str]:
    pmd3path = shutil.which("pymobiledevice3")
    if not pmd3path:
        return [sys.executable, '-m', 'pymobiledevice3']
    return [pmd3path]


class TunnelError(Exception):
    pass


def start_tunnel_one(pmd3_path: List[str], udid: str) -> Tuple[Address, subprocess.Popen]:
    log_prefix = f"[{udid}]"
    start_tunnel_cmd = "remote"
    if udid in get_need_lockdown_devices():
        start_tunnel_cmd = "lockdown"
    cmdargs = pmd3_path + f"{start_tunnel_cmd} start-tunnel --script-mode --udid {udid}".split()
    logger.info("%s cmd: %s", log_prefix, shlex.join(cmdargs))
    process = subprocess.Popen(
        cmdargs, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,creationflags=0x08000000
    )
    output_str = process.stdout.readline().decode("utf-8").strip()
    if output_str == "":
        raise TunnelError("pmd3 start-tunnel empty response")
    address, port_str = output_str.split()
    port = int(port_str)
    logger.info("%s tunnel address: %s", log_prefix, [address, port])
    process.stdout = subprocess.DEVNULL
    return Address(address, port), process


class DeviceManager:
    def __init__(self):
        self.active_monitors: Mapping[str, subprocess.Popen] = {}
        self.running = True
        self.addresses: Mapping[str, Address] = {}
        self.pmd3_cmd = ["pymobiledevice3"]

    def update_devices(self):
        current_devices = set(get_connected_devices())
        active_udids = set(self.active_monitors.keys())

        # Start monitors for new devices
        for udid in current_devices - active_udids:
            self.active_monitors[udid] = None
            try:
                threading.Thread(name=f"{udid} keeper",
                                 target=self._start_tunnel_keeper,
                                 args=(udid,),
                                 daemon=True).start()
            except Exception as e:
                logger.error("udid: %s start-tunnel failed: %s", udid, e)

        # Stop monitors for disconnected devices
        for udid in active_udids - current_devices:
            logger.info("udid: %s quit, terminate related process", udid)
            process = self.active_monitors[udid]
            if process:
                process.terminate()
            self.active_monitors.pop(udid, None)
            self.addresses.pop(udid, None)

    def _start_tunnel_keeper(self, udid: str):
        while udid in self.active_monitors:
            try:
                addr, process = start_tunnel_one(self.pmd3_cmd, udid)
                self.active_monitors[udid] = process
                self.addresses[udid] = addr
                self._wait_process_exit(process, udid)
            except TunnelError:
                logger.exception("udid: %s start-tunnel failed", udid)
            time.sleep(3)

    def _wait_process_exit(self, process: subprocess.Popen, udid: str):
        while True:
            try:
                process.wait(1.0)
                self.addresses.pop(udid, None)
                logger.warning("udid: %s process exit with code: %s", udid, process.returncode)
                break
            except subprocess.TimeoutExpired:
                continue

    def shutdown(self):
        logger.info("terminate all processes")
        for process in self.active_monitors.values():
            if process:
                process.terminate()
        self.running = False

    def run_forever(self):
        while self.running:
            try:
                self.update_devices()
            except Exception as e:
                logger.exception("update_devices failed: %s", e)
            time.sleep(1)

def find_pid_by_port(port: int):
    """
    找出占用指定端口的进程PID，支持Windows和Linux。
    返回PID列表（可能多个进程占用）。
    """
    pids = []
    if sys.platform.startswith("win"):
        # Windows用netstat + findstr
        cmd = f'netstat -ano | findstr :{port}'
        output = subprocess.getoutput(cmd)
        for line in output.splitlines():
            parts = line.strip().split()
            # 解析格式可能是：TCP  0.0.0.0:8000  0.0.0.0:0  LISTENING  PID
            if len(parts) >= 5 and parts[1].endswith(f":{port}"):
                pid = parts[-1]
                if pid.isdigit():
                    pids.append(int(pid))
    else:
        # Linux用lsof或ss
        try:
            output = subprocess.check_output(f"lsof -i:{port} -t", shell=True).decode()
            for line in output.strip().splitlines():
                if line.isdigit():
                    pids.append(int(line))
        except subprocess.CalledProcessError:
            # 没找到占用进程
            pass
    return pids

def kill_process(pid: int):
    try:
        if sys.platform.startswith("win"):
            subprocess.run(f"taskkill /PID {pid} /F", shell=True)
        else:
            os.kill(pid, signal.SIGTERM)
        print(f"已杀死占用端口的进程PID: {pid}")
    except Exception as e:
        print(f"杀死PID {pid} 失败: {e}")


def run_tunneld(pmd3_path: Optional[str] = None, port: int = 5555):
    """
    启动 iOS >=17 设备自动tunnel服务，后台线程启动，不阻塞当前线程

    :param pmd3_path: pymobiledevice3 cli 路径，默认自动查找
    :param port: 监听端口，默认9527
    """
    pids = find_pid_by_port(port)
    if pids:
        print(f"端口 {port} 被占用，准备杀掉相关进程...")
        for pid in pids:
            kill_process(pid)
        # 给系统一点时间释放端口
        time.sleep(1)

    if not os_utils.is_admin:
        logger.error("Please run as root(Mac) or administrator(Windows)")
        sys.exit(1)

    manager = DeviceManager()
    app = FastAPI()

    @app.get("/")
    def get_devices():
        return manager.addresses

    @app.get("/shutdown")
    def shutdown():
        manager.shutdown()
        os.kill(os.getpid(), signal.SIGINT)
        return Response(status_code=200, content="Server shutting down...")
    
    if not shutil.which("pymobiledevice3"):
        return
    
    if pmd3_path is None:
        manager.pmd3_cmd = guess_pymobiledevice3_cmd()
    else:
        manager.pmd3_cmd = [pmd3_path]

    # 启动设备管理后台线程
    threading.Thread(
        target=manager.run_forever,
        daemon=True,
        name="device_manager"
    ).start()

    # 把 uvicorn 服务器启动放进线程，且设置为守护线程
    def run_uvicorn():
        uvicorn.run(app, host="0.0.0.0", port=port, log_config=None)

    thread = threading.Thread(target=run_uvicorn, daemon=True, name="uvicorn_server")
    thread.start()

    logger.info("Tunnel service started in background thread.")
