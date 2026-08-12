
import plistlib
from queue import Queue, Empty
import threading
import time
from logzero import logger
from dataclasses import fields
from pymobiledevice3.lockdown import LockdownClient
from pymobiledevice3.services.dvt.dvt_secure_socket_proxy import DvtSecureSocketProxyService
from pymobiledevice3.services.dvt.instruments.sysmontap import Sysmontap


def parse_row(row):
    if isinstance(row, dict):
        return row
    elif isinstance(row, bytes):
        return plistlib.loads(row)
    elif isinstance(row, str):
        return plistlib.loads(row.encode())
    else:
        raise TypeError(f"Unsupported row type: {type(row)}")


class SystemMonitor:
    def __init__(self, service_provider: LockdownClient, pid: str):
        self.service_provider = service_provider
        self.pid = pid
        self.running = False
        self._thread = None
        self._queue = Queue()
        self.latest_stats = None

    def _convert_bytes(self, val):
        if val is None:
            return "0"
        return f"{round(val / 1048576, 2)}"

    def _worker(self):
        with DvtSecureSocketProxyService(lockdown=self.service_provider) as dvt:
            sysmontap = Sysmontap(dvt)
            system_fields = [f.name for f in fields(sysmontap.system_attributes_cls)]
            process_attributes = [f.name for f in fields(sysmontap.process_attributes_cls)]
            with sysmontap as sysmon:
                pid = self.pid
                full_stats = {
                    "cpu_data": {},
                    "system_info": {},
                    "app_data": {},
                }
                cpu_count = 6  # 默认 CPU 数量
                for row in sysmon:
                    if not self.running:
                        break

                    cpu_info = {}
                    system_info = {}
                    app_data = {}
                    # CPU 信息
                    try:
                        cpu_data = row.get("PerCPUUsage")
                    except:
                        continue

                    if cpu_data:
                        cpu_count = row.get("CPUCount", cpu_count)
                        total_load = row.get("SystemCPUUsage", {}).get("CPU_TotalLoad", 0)
                        per_cpu = row.get("PerCPUUsage", [])
                        if isinstance(per_cpu, dict):
                            per_cpu = list(per_cpu.values())

                        cpu_info["CPUCount"] = cpu_count
                        cpu_info["SystemCPUUsage"] = f"{round(total_load / cpu_count, 2)}"
                        cpu_info["PerCPUUsage"] = [
                            f"{round(cpu.get('CPU_TotalLoad', 0), 2)}" for cpu in per_cpu
                        ]

                        system_values = row.get("System", [])
                        system_info = dict(zip(system_fields, system_values))

                    # 进程信息
                    processes = row.get("Processes", {})
                    jinchen = processes.get(int(pid), {})
                    if jinchen:
                        app_data = dict(zip(process_attributes, jinchen))

                    # 仅当有新数据时才更新对应部分
                    if cpu_info:
                        full_stats["cpu_data"] = cpu_info
                    if system_info:
                        full_stats["system_info"] = system_info
                    if app_data:
                        full_stats["app_data"] = app_data
                    self.latest_stats = full_stats
                    self._queue.put(full_stats)
                    time.sleep(0.5)

    def start(self):
        if self.running:
            logger.warning("SystemMonitor is already running.")
            return
        self.running = True
        self._thread = threading.Thread(target=self._worker, daemon=True)
        self._thread.start()
        logger.info("System monitoring started.")

    def stop(self):
        if not self.running:
            logger.warning("SystemMonitor is not running.")
            return
        self.running = False
        self._thread.join()
        logger.info("System monitoring stopped.")

    def get_latest(self):
        """获取最新采样帧（dict）"""
        return self.latest_stats

    def get_all(self, timeout=1, clear_queue=False):
        """获取全部历史采样（列表）"""
        results = []
        while True:
            try:
                item = self._queue.get(timeout=timeout)
                results.append(item)
            except Empty:
                break
        if clear_queue:
            with self._queue.mutex:
                self._queue.queue.clear()
        return results
