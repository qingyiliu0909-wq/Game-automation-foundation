import socket
import time
from typing import Optional
from pymobiledevice3.lockdown import create_using_usbmux, usbmux
from pymobiledevice3.lockdown_service_provider import LockdownServiceProvider
from pymobiledevice3.remote.remote_service_discovery import RemoteServiceDiscoveryService
from DeviceControl.idevice.utils.exceptions import FatalError
import requests

import datetime
from pydantic import BaseModel


class DeviceShortInfo(BaseModel):
    BuildVersion: str
    ConnectionType: Optional[str]
    DeviceClass: str
    DeviceName: str
    Identifier: str
    ProductType: str
    ProductVersion: str


class ProcessInfo(BaseModel):
    isApplication: bool
    pid: int
    name: str
    realAppName: str
    startDate: datetime.datetime
    bundleIdentifier: Optional[str] = None
    foregroundRunning: Optional[bool] = None


def list_devices():
    return usbmux.list_devices(None)


#设备相关文件
class EnterableRemoteServiceDiscoveryService(RemoteServiceDiscoveryService):
    async def __aenter__(self):
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

def is_port_open(ip: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex((ip, port)) == 0

def connect_remote_service_discovery_service(udid: str, tunneld_url: Optional[str] = None) -> EnterableRemoteServiceDiscoveryService:
    if tunneld_url is None:
        if is_port_open("localhost", 49151):
            tunneld_url = "http://localhost:49151"
        elif is_port_open("localhost", 9527):
            tunneld_url = "http://localhost:9527"
        elif is_port_open("localhost", 5555):
            tunneld_url = "http://localhost:5555"
        else:
            print("没启动隧道")
    try:
        resp = requests.get(tunneld_url, timeout=60)
        tunnels = resp.json()
        if "60105" in tunneld_url:
            for tunn in tunnels:
                if udid==tunn.get("udid"):
                    ipv6_address=[tunn.get("address"),tunn.get("rsdPort")]
                    print(ipv6_address)
        else:
            ipv6_address = tunnels.get(udid)
        if ipv6_address is None:
            raise FatalError("tunneld not ready for device", udid)
        rsd = EnterableRemoteServiceDiscoveryService(ipv6_address)
        return rsd
    except requests.RequestException:
        raise FatalError("Please run `sudo t3 tunneld` first")
    except (TimeoutError, ConnectionError):
        raise FatalError("RemoteServiceDiscoveryService connect failed")

def connect_service_provider(udid: Optional[str], force_usbmux: bool = False, usbmux_address: Optional[str] = None) -> LockdownServiceProvider:
    lockdown = create_using_usbmux(serial=udid, usbmux_address=usbmux_address)
    if force_usbmux:
        return lockdown
    if lockdown.product_version >= "17":
        return connect_remote_service_discovery_service(lockdown.udid)
    return lockdown

