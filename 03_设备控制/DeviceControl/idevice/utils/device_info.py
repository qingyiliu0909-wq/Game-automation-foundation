from pydantic import BaseModel
import datetime
from typing import Optional, Iterator

from pymobiledevice3.services.diagnostics import DiagnosticsService
from pymobiledevice3.services.dvt.dvt_secure_socket_proxy import DvtSecureSocketProxyService
from pymobiledevice3.services.dvt.instruments.device_info import DeviceInfo

#设备信息进程信息

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

def proclist(service_provider) -> Iterator[ProcessInfo]:
    with DvtSecureSocketProxyService(lockdown=service_provider) as dvt:
        processes = DeviceInfo(dvt).proclist()
        for process in processes:
            if 'startDate' in process:
                process['startDate'] = str(process['startDate'])
            yield ProcessInfo.model_validate(process)


def reboot_devices(service_provider):
    with DiagnosticsService(service_provider) as diagnostics:
        diagnostics.restart()

def get_battery(service_provider):
    with DiagnosticsService(service_provider) as diagnostics:
       return  diagnostics.get_battery()