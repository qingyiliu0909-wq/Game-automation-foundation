import requests,traceback
from loguru import logger
import config

class DeviceControlBase(object):
    def __init__(self, DeviceName,Devices,Device_IP, Control_Type,PackageUrl,PackageInfo={}, DeviceID=0,Device_Parameters={}):
        self.Platform=""
        self.DID = DeviceID
        self.DName = DeviceName
        self.Devices=Devices
        self.Device_IP=Device_IP
        self.PackageUrl=PackageUrl
        self.PackageInfo=PackageInfo
        self.Control_Type=Control_Type
        self.GamePath=""
        self.Device_Parameters = Device_Parameters
        self.IControl=None# 存放设备的控制类(PC 句柄,android u2, ios:tidevice)

    def Initialization(self):
        # 包名和游戏名 暂且认为是相同的
        self.GameName="EM"   
        self.Game_Activity="" 

    def Check_IP(self):
        """检查设备ip"""
        try:
            device_ip=self.GetDeviceIP()
            if device_ip!=None and "10." in device_ip and device_ip!=self.Device_IP:
                logger.info(f"需要更新设备IP {device_ip}")
                self.Device_IP=device_ip
                data={"ip":device_ip,"id":self.DID}
                ret=requests.get(f"{config.UAutoServer}/device/update_device_ip",params=data).text
                logger.info(f"设备信息更新完成{ret}")
            return self.Device_IP
        except:
            logger.warning(traceback.format_exc())
            return self.Device_IP
    
    def DeviceIsOnline(self):
        return True

    def GetDeviceIP(self):
        """获取设备ip"""
        return self.Device_IP
    
    def GetDeviceState(self): 
        """获取设备状态"""
        pass
    def UnOrlockDevice(self,Islock:bool): 
        """解锁设备/关闭设备"""
        pass
    def Install_Package(self):
        """安装应用"""
        pass
    def UNInstall_Package(self):
        """卸载应用"""
        pass
    def StartGame(self):
        """启动游戏"""
        pass
    def ClosePopUpWindow(self):
        """关闭弹窗"""
        pass
    def StopGame(self):
        """终止游戏"""
        pass
    def GetAllAPP(self):
        """获取设备所以应用程序"""
        pass
    def GetAPPInfo(self):
        """获取应用信息"""
        pass
    def AppsIsRun(self):
        """应用是否正在运行"""
        pass
    def ClickScreen(self,x,y,duration=0):
        """点击屏幕坐标"""
        pass
    def SlideScreen(self,x,y,x1,x2,duration=0):
        """滑动屏幕"""
        pass
    def MoveAndScroll(self,x,y,distance):
        """移动的指定位置并点击"""
    def GetScreenshot(self,file_path="",file_name=""):
        """获取截屏 返回路径"""
        pass
    def get_log_url(self,casename=""):
        "获取日志的URL"
        pass
    def get_utrace_url(self,casename=""):
        "获取采集的utrace文件 URL"
        pass
    def get_new_csv_file(self,file_path=""):
        "获取采集的csv文件"
        pass
    def Is_Recording(self) -> bool:
        pass
    def Start_Recording(self, file_path="",file_name="",quality="low"):
        """
        屏幕录制 返回路径
        """
        pass
    def Stop_Recording(self):
        """停止录制并保存文件"""
        pass