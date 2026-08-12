from loguru import logger
import sys,socket
from DeviceControl.ControlBase import DeviceControlBase
from DeviceControl.AndroidControl import AndroidDevice
from DeviceControl.IOSControl import IOSDevice
from DeviceControl.idevice.idevice_api import get_devices_list
from enum import Enum
import uuid
from DeviceControl.PCControl import PCDevice
import adbutils,os,psutil
from tidevice import Usbmux

#所有的平台类型使用枚举进行传输
class DeviceOS(Enum):
    Android = "android"
    IOS = "ios"
    PC = "PC"

def get_disk_free():
    # 获取磁盘使用情况
    disk_usage = psutil.disk_usage(os.getcwd()[:3])
    return int(disk_usage.free/1027/1024/1024)

def GetDeviceOSEnumType(platform:str) -> DeviceOS:
    print(platform)
    if platform.lower()== "android":
        return DeviceOS.Android
    elif platform.lower()== "ios":
        return DeviceOS.IOS
    elif platform.lower()== "pc":
        return DeviceOS.PC
    else:
        raise ValueError(f"This {platform} type is not supported")
adb=None
tios=None
def GetConnectedDevices():
    global adb,tios
    """获取所有连接的设备"""
    if adb==None and tios==None:
        adb= adbutils.AdbClient()
        tios  = Usbmux()
    devices=[]
    #PC
    if sys.platform=="win32":
        devices.append(str(uuid.getnode()))
    #安卓
    for device in adb.list():
        if device.state=="device":
            devices.append(device.serial)
    #ios
    try:
        if tios!=None:
            all_ios=tios.device_list()
            for i in all_ios:
                devices.append(i.udid)
    except:
        tios=None
        logger.warning("设备没有装itunes 无法支持ios设备")
       
    # logger.info(devices)
    return devices

_instances={}
def GetDeviceControl(name:DeviceOS,*args):
    global _instances
    if name == DeviceOS.Android:
        if DeviceOS.Android not in _instances:
            _instances[DeviceOS.Android]=AndroidDevice(*args)
        else:
            print(DeviceOS.Android,"已经初始化过 返回实例")
        return _instances[DeviceOS.Android]
    
    elif name == DeviceOS.IOS:
        if DeviceOS.IOS not in _instances:
            _instances[DeviceOS.IOS]=IOSDevice(*args)
        else:
            print(DeviceOS.IOS,"已经初始化过 返回实例")
        return _instances[DeviceOS.IOS]
    
    elif name == DeviceOS.PC:
        if DeviceOS.PC not in _instances:
            _instances[DeviceOS.PC]=PCDevice(*args)
        else:
            print(DeviceOS.PC,"已经初始化过 返回实例")
        return _instances[DeviceOS.PC]
    
    else:
        raise ValueError("This os type is not supported")


if __name__ ==  "__main__":
    mux = Usbmux()
    tios = mux.device_list()
    for i in tios:
        print(i)
        # devices.append(i.udid)
