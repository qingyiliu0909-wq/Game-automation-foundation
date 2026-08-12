
from pymobiledevice3.services.syslog import SyslogService
from pymobiledevice3.services.pcapd import PcapdService
from DeviceControl.idevice.utils.device import connect_service_provider, list_devices, create_using_usbmux, \
    connect_remote_service_discovery_service
from DeviceControl.idevice.utils.device_info import proclist, DeviceShortInfo, ProcessInfo,reboot_devices,get_battery
from DeviceControl.idevice.utils.app_management import (
    app_install,
    app_uninstall,
    app_launch,
    app_info,
    get_running_pid,
    kill_running_from_pid,
    get_app_list
)
import requests
from DeviceControl.idevice.utils.IPV4 import *
from DeviceControl.idevice.utils.relay import TcpRelay
from DeviceControl.idevice.utils.system_perf import SystemMonitor
from DeviceControl.idevice.utils.GPU_perf import GPU
from DeviceControl.idevice.utils.fps_perf import FPS as FPSMonitor
from DeviceControl.idevice.utils.Network import NetworkSampler
from DeviceControl.idevice.utils.Energy import EnergySampler
from zeroconf._utils import *
from zeroconf._handlers.answers import *
from zeroconf._utils.ipaddress import *
from pyimg4 import *
from pyimg4 import IM4P
from pymobiledevice3.exceptions import AlreadyMountedError, InvalidServiceError
from pymobiledevice3.common import get_home_folder
from pymobiledevice3.services.amfi import AmfiService
from packaging.version import Version
import shutil
import time
from PIL import Image
from io import BytesIO
import asyncio
import os
import sys
from DeviceControl.idevice.utils.fsync import AFCFileClient
from DeviceControl.idevice.utils.screenshot import screenshot, screenshot_png
from DeviceControl.idevice.utils.developer_mode import enable_developer_mode
import warnings

warnings.filterwarnings("ignore", category=DeprecationWarning)


def safe_create_idevice(udid, retry=3):
    for _ in range(retry):
        try:
            return Idevices(udid=udid)
        except ConnectionAbortedError as e:
            print(f"[Warning] 连接中断，重试中: {e}")
            time.sleep(2)
    raise RuntimeError(f"无法连接设备 {udid}")


def get_devices_list():
    return list_devices()

class NetworkInfo:
    def __init__(self):
        self.mac = ""
        self.ipv4 = ""
        self.ipv6 = ""



def safe_rename(src, dst, max_retry=5, delay=0.5):
    for i in range(max_retry):
        try:
            shutil.move(src, dst)
            return
        except PermissionError:

            time.sleep(delay)


import asyncio

def run_async_in_thread(coro):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    return loop.run_until_complete(coro)

def is_tunneld_running(port: int = 5555) -> bool:
    try:
        r = requests.get(f"http://127.0.0.1:{port}/", timeout=0.5)
        return r.status_code == 200
    except Exception:
        return False

class Idevices:
    def __init__(self, udid, max_retry=3, retry_interval=2):
        self.EnergySampler = None
        self.NetworkSampler = None
        self.FPSMonitor = None
        self.udid = udid
        self.TcpRelay=None
        self.os_version = False
        lockdown = create_using_usbmux(serial=udid, usbmux_address=None)
        self.product_version=lockdown.product_version
        self.product_type=lockdown.product_type
        self.unique_chip_id = lockdown.unique_chip_id
        self.device_public_key = lockdown.device_public_key
        self.DVTMonitor=None
        self.System=None
        self.bundle_id=None
        if int(lockdown.product_version.split(".")[0]) >= 17:
            self.os_version = True
            if not is_tunneld_running(5555):
                from tidevice3.cli.tunneld import tunneld
                import threading
                threading.Thread(
                    target=lambda: tunneld.main(
                        args=["--port", "5555"],
                        standalone_mode=False,
                    ),
                    daemon=True,
                    name="tunneld-runner",
                ).start()
                time.sleep(4)
                print("启动t3隧道成功")

            self.rsd = connect_remote_service_discovery_service(lockdown.udid)

            # 连接重试机制
            for attempt in range(max_retry):
                try:
                    self._run_async_sync(self.rsd.connect())
                    break  # 连接成功，跳出重试循环
                except asyncio.exceptions.TimeoutError:
                    print(f"[{attempt + 1}/{max_retry}] 连接超时，等待 {retry_interval}s 后重试...")
                    time.sleep(retry_interval)
                except Exception as e:
                    print(f"[{attempt + 1}/{max_retry}] 连接异常: {e}")
                    time.sleep(retry_interval)
            else:
                # 如果所有重试都失败，可以选择抛异常或者设置某种失败状态
                raise RuntimeError(f"连接远程服务失败，超过最大重试次数 {max_retry}")
        else:
            self.rsd = connect_service_provider(udid=udid)

    def get_product_type(self):
        return self.rsd.product_type

    def get_ip(self):
        mac = self.rsd.get_value("", "WiFiAddress")

        class NetworkInfo:
            def __init__(self, mac):
                self.mac = mac
                self.ipv4 = ""
                self.ipv6 = ""

        info = NetworkInfo(mac)
        pcap = PcapdService(self.rsd)

        for packet in pcap.watch(packets_count=100):
            # 这里确保用 scapy 解析完整的以太网包
            scapy_packet = Ether(packet.data)
            # print(scapy_packet)
            find_ip(scapy_packet, info)
            if info.ipv4 and info.ipv6:
                # print(f"Found IPs: IPv4={info.ipv4}, IPv6={info.ipv6}")
                return info.ipv4

        # print("IPv4 not found in packets, return empty string or None")
        return info.ipv4

    def _run_async_sync(self, coro):
        """在新的事件循环里同步运行异步函数，避免事件循环冲突"""
        loop = asyncio.new_event_loop()
        try:
            asyncio.set_event_loop(loop)
            return loop.run_until_complete(coro)
        finally:
            loop.close()
            asyncio.set_event_loop(None)  # 解除事件循环绑定，防止遗留

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        try:
            pass
            # if hasattr(self, 'rsd') and hasattr(self.rsd, 'close'):
                # self._run_async_sync(self.rsd.close())
        except Exception as e:
            sys.__stderr__.write(f"Exception during rsd close: {repr(e)}\n")

    def get_os(self):
        return self.os_version
    
    def get_product_version(self):
        return self.product_version

    def screenshot_jpg(self, save_path=None, quality=10):  # 降低画质，默认30
        img_bytes = screenshot_png(self.rsd)
        img = Image.open(BytesIO(img_bytes))

        if save_path is None:
            save_path = "default.jpg"

        save_dir = os.path.dirname(save_path)
        if save_dir and not os.path.exists(save_dir):
            os.makedirs(save_dir)

        print(f"Saving to {save_path} with quality={quality}")
        img.save(save_path, format="JPEG", quality=quality)

    def install_app(self,url_or_path):#安装app
        lockdown = create_using_usbmux(serial=self.udid, usbmux_address=None)
        return app_install(lockdown,url_or_path)

    def uninstall_app(self,bounld_id):#卸载app
        return app_uninstall(self.rsd,bounld_id)

    def reboot(self):
        """重启设备"""
        reboot_devices(self.rsd)


    def launch(self,bounld_id):
        """启动应用"""
        app_launch(self.rsd,bounld_id)

    def get_app_info(self,bounld_id):
        """启动应用"""
        return app_info(self.rsd,bounld_id)


    def get_pid(self,bounld_id):
        """获取应用运行的pid"""
        return get_running_pid(self.rsd,bounld_id)


    def kill_ipa(self,bounld_id):
        """根据传入的包名杀掉进程"""
        kill_running_from_pid(self.rsd,self.get_pid(bounld_id))


    def start_developer(self):
        """根据传入的包名杀掉进程"""
        return enable_developer_mode(self.rsd)

    def push(self,bundle_id,file_path,device_path):
        """推送文件
        file_path:文件地址
        device_path:远程本地文件地址
        """
        afc=AFCFileClient(self.rsd,bundle_id)
        afc.push(file_path,device_path)

    def pull(self, bundle_id, local_path, device_path, remove=False, local_rename=None):
        """
        获取文件
        :param bundle_id: app bundle id
        :param local_path: 本地保存路径（目录或文件路径）
        :param device_path: 设备文件路径
        :param remove: 是否删除设备上的文件
        :param local_rename: 拉取后本地文件改名，传文件名（非路径）
        """
        afc = AFCFileClient(self.rsd, bundle_id)

        # 先拉取设备文件到本地，使用local_path作为目录或文件名
        afc.pull(device_path, local_path)
        # 如果指定了改名，重命名本地文件
        if local_rename:
            if os.path.isdir(local_path):
                original_filename = os.path.basename(device_path)
                original_file_path = os.path.join(local_path, original_filename)
                new_file_path = os.path.join(local_path, local_rename)
            else:
                original_file_path = local_path
                new_file_path = os.path.join(os.path.dirname(local_path), local_rename)

            safe_rename(original_file_path, new_file_path)


        if remove:
            afc.remove(device_path)

    def rm(self,bundle_id,file_path):
        """删除文件
        file_path:设备内文件地址
        """
        afc=AFCFileClient(self.rsd,bundle_id)
        afc.remove(file_path)

    def ls(self,bundle_id,file_path):
        """获取文件内容
        file_path:设备内文件地址
        """
        afc=AFCFileClient(self.rsd,bundle_id)
        return  afc.list_dir(file_path)

    def get_app_list_info(self):
        """获取设备所有应用程序
        app["CFBundleIdentifier"], app.get("CFBundleDisplayName"), app.get("version")
        com.panstudio.duetnightabyss.arpg.global Duet Night Abyss 1.0.3
        """
        return get_app_list(self.rsd)

    def GetAllAPP(self):
        """获取设备所有应用程序
        app["CFBundleIdentifier"], app.get("CFBundleDisplayName"), app.get("version")
        com.panstudio.duetnightabyss.arpg.global Duet Night Abyss 1.0.3
        """
        app_list = []
        for app in  get_app_list(self.rsd):
            print
            bundle_id = app['CFBundleIdentifier']
            app_list.append(bundle_id)
        return app_list

    def GetAPPVersion(self, bundle_id: str):
        """
        获取指定 App 的版本信息

        参数:
            bundle_id (str): 要查询的 App 的 CFBundleIdentifier

        返回:
            dict: {
                "version": 主版本号（CFBundleShortVersionString）,
                "build": 构建号（CFBundleVersion）
            }
            如果找不到对应 App，返回空字符串字段
        """
        for app in get_app_list(self.rsd):
            if app.get("CFBundleIdentifier") == bundle_id:
                version=app.get('CFBundleShortVersionString', '')
                versioncode = app.get('CFBundleVersion', '')
                return "{}.{}".format(version,versioncode)
        return "0.0"

    def syslog(self):
        """获取系统日志"""
        max_retry=4
        retry_interval=2
        lockdown = create_using_usbmux(serial=self.udid, usbmux_address=None)
        # 判断版本号
        if int(lockdown.product_version.split(".")[0]) >= 17:
            self.os_version = True
            lockdown = connect_remote_service_discovery_service(self.udid)
            for attempt in range(max_retry):
                try:
                    self._run_async_sync(lockdown.connect())
                    break  # 连接成功，跳出重试循环
                except asyncio.exceptions.TimeoutError:
                    print(f"[{attempt + 1}/{max_retry}] 连接超时，等待 {retry_interval}s 后重试...")
                    time.sleep(retry_interval)
                except Exception as e:
                    print(f"[{attempt + 1}/{max_retry}] 连接异常: {e}")
                    time.sleep(retry_interval)

        syslog_service = SyslogService(lockdown)
        return  syslog_service.watch()

    def enable_developer_mode(self):
        """ enable developer mode """
        # 启用开发者模式
        if Version(self.rsd.product_version) >= Version("16"):
            if not self.rsd.developer_mode_status:

                AmfiService(self.rsd).enable_developer_mode()
            else:
                print('developer mode already enabled')

        try:
            xcode = get_home_folder() / 'Xcode.app'
            xcode.mkdir(parents=True, exist_ok=True)
            # auto_mount(self.rsd, xcode=xcode)
            print('mount developer image')
        except AlreadyMountedError:
            print('developer image already mounted')


    def get_batteryinfo(self):
        """ enable developer mode """
        # 启用开发者模式
        return get_battery(self.rsd)

    def start_gpu(self):
        if not self.DVTMonitor:
            self.DVTMonitor=GPU(self.rsd)
        self.DVTMonitor.start()


    def get_gpu(self):
        if not self.DVTMonitor:
            self.DVTMonitor=GPU(self.rsd)
        return self.DVTMonitor.get_latest()

    def stop_gpu(self):
        if not self.DVTMonitor:
            self.DVTMonitor=GPU(self.rsd)
        self.DVTMonitor.stop()

    def start_system(self,bundle_id):
        if not self.System:
            if self.bundle_id==None:
                self.bundle_id=bundle_id
            self.System=SystemMonitor(self.rsd,self.get_pid(self.bundle_id))
        self.System.start()


    def get_system(self):
        if not self.System:
            self.System = SystemMonitor(self.rsd, self.get_pid(self.bundle_id))
        return self.System.get_latest()

    def stop_system(self):
        if not self.System:
            self.System = SystemMonitor(self.rsd, self.get_pid(self.bundle_id))
        self.System.stop()

    def start_fps(self):
        if not self.FPSMonitor:
            self.FPSMonitor = FPSMonitor(self.rsd)
        self.FPSMonitor.start()

    def get_fps(self):
        if not self.FPSMonitor:
            self.FPSMonitor = FPSMonitor(self.rsd)
        return self.FPSMonitor.get_latest()

    def stop_fps(self):
        if not self.FPSMonitor:
            self.FPSMonitor = FPSMonitor(self.rsd)
        self.FPSMonitor.stop()


    def start_network(self,bundle_id):
        if not self.NetworkSampler:
            if self.bundle_id==None:
                self.bundle_id=bundle_id
            self.NetworkSampler = NetworkSampler(self.rsd,self.get_pid(self.bundle_id))
        self.NetworkSampler.start()

    def get_network(self):
        if not self.NetworkSampler:
            self.NetworkSampler = NetworkSampler(self.rsd,self.get_pid(self.bundle_id))
        return self.NetworkSampler.get_latest()

    def stop_network(self):
        if not self.NetworkSampler:
            self.NetworkSampler = NetworkSampler(self.rsd,self.get_pid(self.bundle_id))
        self.NetworkSampler.stop()


    def start_entergy(self,bundle_id):
        if not self.EnergySampler:
            if self.bundle_id==None:
                self.bundle_id=bundle_id
            self.EnergySampler = EnergySampler(self.rsd,self.get_pid(bundle_id))
        self.EnergySampler.start()

    def get_entergy(self):
        if not self.EnergySampler:
            self.EnergySampler = EnergySampler(self.rsd, self.self.get_pid(self.bundle_id))
        return self.EnergySampler.get_latest()

    def stop_entergy(self):
        if not self.EnergySampler:
            self.EnergySampler = EnergySampler(self.rsd, self.get_pid(self.bundle_id))
        self.EnergySampler.stop()

    def relay_start(self,local_port=9100, device_port=9100):
        if not self.TcpRelay:
            self.TcpRelay=TcpRelay(self.rsd, device_port, local_port)
        self.TcpRelay.start_relay()


    def relay_stop(self):
        self.TcpRelay.stop_relay()