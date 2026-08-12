from datetime import datetime
from DeviceControl.ControlBase import DeviceControlBase
from loguru import logger
import adbutils
import time,config,os,json
from xml.etree import cElementTree as ET
from utils import util
import threading
import urllib.parse
import subprocess
import traceback

class AndroidDevice(DeviceControlBase):
    def __init__(self, DeviceName,Devices,Device_IP, Control_Type=0, PackageUrl="",PackageInfo={}, DeviceID=0,Device_Parameters={}):
        super().__init__(DeviceName,Devices,Device_IP, Control_Type, PackageUrl,PackageInfo, DeviceID, Device_Parameters)
        self.Platform="Android"
        self.Control_Type=Control_Type
        self.adb=adbutils.AdbClient(host="127.0.0.1", port=5037)
        self.connect=None
        self.logcat=None
        self.stop_event = threading.Event()
        self.logcat_file_path=""
        self.recording_process = None
        # adb shell dumpsys window | findstr mCurrentFocus 查看运行程序的包名和Activity名字
        
    def Initialization(self):
        if int(self.Control_Type)==1:
            self.adb.connect(self.Device_IP, 5555)
        self.connect=self.adb.device(self.Devices)
        if self.connect==None:
            raise ConnectionError("设备不存在 连接失败")
        logger.info("初始化完成")

    def DeviceIsOnline(self):
        for device in self.adb.device_list():
            if device.serial ==self.Devices:
                print("设备不在线")
                return True
        print("设备不在线")
        return False

    def GetDeviceIP(self):
        try:
            ip_str_arr = self.connect.shell("ip route show").split("\n")
            for item1 in ip_str_arr:
                if "wlan" in item1 and "src" in item1:
                    for index, item2 in enumerate(item1.split()):
                        if item2 == "src":
                            return item1.split()[index + 1]
        except:
            pass
        return ""
    
    def GetDeviceState(self): 
        """获取设备状态"""
        return self.connect.is_screen_on()
    
    def UnOrlockDevice(self,lock:bool): 
        """解锁设备/关闭设备"""
        if lock : 
            if self.GetDeviceState(): #当手机为息屏状态时候
                self.connect.keyevent("26")
                time.sleep(1)
        else:
            res=self.connect.shell("dumpsys window | grep mCurrentFocus")
            if "NotificationShade" in res:
                logger.info("设备处于锁屏状态")
                wh:str=self.connect.shell("wm size")
                size = wh.replace(" ", "").replace('\n', '').split(":")[1].split("x")
                self.connect.shell(f"input swipe {int(size[0])/2} {int(size[1])*0.8} {int(size[0])/2} {int(size[1])*0.4}")
                logger.info("Are unlocked screen")
        return True

    def Install_Package(self):
        """安装应用"""
        packages = self.connect.list_packages()
        if self.PackageInfo["name"] in packages:
            app_info = self.connect.app_info(self.PackageInfo["name"])
            logger.info(app_info)
            if f"{app_info.version_name}" not in self.PackageInfo["version"]:
                logger.info("包版本不一致!! 更新并清理缓存")
                self.connect.app_clear(self.PackageInfo["name"])
            else:
                logger.info("包版本一致, 跳过安装")
                return True

        file_path = util.DownloadFile(self.PackageUrl)
        popup_thread = self.MonitorInstallPopups()
        self.connect.install(file_path,flags=["-r","-t","-d"])
        self.stop_event.set()
        popup_thread.join()
        logger.info("安装完成")
        return True

    def MonitorInstallPopups(self):
        """启动一个线程监控安装弹窗"""
        logger.info("启动安装弹窗监控线程")
        popup_thread = threading.Thread(target=self.Click_Install_pop)
        popup_thread.daemon = True
        popup_thread.start()
        return popup_thread
    def UNInstall_Package(self):
        """卸载应用"""
        logger.warning("卸载包体!!")
        self.connect.uninstall(self.PackageInfo["name"])

    def StartGame(self,command=""):
        """启动游戏"""
        logger.warning("启动游戏!!")
        if self.AppsIsRun():
            self.StopGame()
            time.sleep(4)
        self.logcat_file_path = f"{config.DownloadGameLogPath}/{self.DName}_{datetime.now().strftime(f'Android-%Y-%m-%d_%H-%M-%S.log')}"
        self.logcat=self.connect.logcat(self.logcat_file_path,clear=True)
        ucmdpath=f"{config.DownloadGameLogPath}\\{self.DName}"
        if not os.path.exists(ucmdpath):os.makedirs(ucmdpath)
        ucmdpath=ucmdpath+"\\ue4commandline.txt"
        if command!= "":
            with open(ucmdpath,"w+") as f:f.write(command)
            remote_path = f"/storage/emulated/0/Android/data/{self.PackageInfo['name']}/files/UE4Game/{self.PackageInfo['project']}"
            if self.file_exits(remote_path,self.PackageInfo['project']):
                self.push(ucmdpath,remote_path)#推送文件过去
                time.sleep(1)
            else:
                logger.warning("进行推送文件,但远程的文件夹并不存在")
        ret=self.connect.shell(["am", "start", "-W", "-n", self.PackageInfo["name"] + "/" + self.PackageInfo["activity"]])
        logger.info("启动时间为: "+ret)
        time.sleep(10)
        if command!= "":
            # print(12345648789)
            self.connect.remove(f"/storage/emulated/0/Android/data/{self.PackageInfo['name']}/files/UE4Game/{self.PackageInfo['project']}/ue4commandline.txt")
        self.ClosePopUpWindow()
        time.sleep(5)
        return self.AppsIsRun()
    
    def get_HierarchyData(self):
        HierarchyData={}
        try:
            HierarchyDataStr=self.connect.dump_hierarchy()
            for neighbor in ET.fromstring(HierarchyDataStr).iter('node'):
                HierarchyData[neighbor.attrib["text"]]=neighbor.attrib["bounds"].replace("][",",").replace("]","").replace("[","")
        except:
            logger.error("获取安卓UI层级失败")
        return HierarchyData

    def clickButtonByText(self,TName):
        """关闭弹窗"""
        # return True
        # HierarchyData 为界面的UI层级对象
        HierarchyData=self.get_HierarchyData()
        for neighbor in HierarchyData:
            if TName!="" and TName in neighbor:
                x1,y1,x2,y2=neighbor[neighbor].split(",")
                self.ClickScreen((int(x2)+int(x1))/2,(int(y2)+int(y1))/2)
                logger.warning(f" 点击了 {TName} 坐标为 {x1,y1,x2,y2}")
                time.sleep(0.2)

    def Click_Install_pop(self):
        """关闭弹窗"""
        # HierarchyData 为界面的UI层级对象
        is_shuru=False
        is_liaojie=False
        while not self.stop_event.is_set():
            HierarchyData=self.get_HierarchyData()
            if "输入帐号密码" in HierarchyData and not is_shuru:
                self.connect.shell("input text 'onlyyingxiong02'")
                logger.warning(f" 输入了密码onlyyingxiong02")
                is_shuru = True
            if "输入锁屏密码" in HierarchyData and not is_shuru:
                self.connect.shell("input text 'pan123456'")
                logger.warning(f" 输入了密码pan123456")
                is_shuru = True
            for neighbor in HierarchyData:
                if "已了解" in neighbor  and not is_liaojie:
                    x1,y1,x2,y2=HierarchyData[neighbor].split(",")
                    self.ClickScreen((int(x2)+int(x1))/2,(int(y2)+int(y1))/2)
                    logger.warning(f" 点击了 {neighbor} 坐标为 {x1,y1,x2,y2}")
                    time.sleep(3.5)
                    is_liaojie = True
                if neighbor in ["允许","继续安装","安装","同意","好","始终允许","确认","确定","完成"]:
                    x1,y1,x2,y2=HierarchyData[neighbor].split(",")
                    self.ClickScreen((int(x2)+int(x1))/2,(int(y2)+int(y1))/2)
                    logger.warning(f" 点击了 {neighbor} 坐标为 {x1,y1,x2,y2}")
                    time.sleep(3.5)
    
    def ClosePopUpWindow(self):
        """关闭弹窗"""
        # HierarchyData 为界面的UI层级对象
        for _i in range(6):
            HierarchyData=self.get_HierarchyData()
            isexit=False
            for neighbor in HierarchyData:
                if neighbor in  ["二重螺旋没有响应"]:
                    raise Exception("出现了无响应!")
                if  neighbor in ["无限制","允许","继续安装","安装","同意","好","确定","始终允许","允许全部","全部允许","无限制","稍后再说"]:
                    x1,y1,x2,y2=HierarchyData[neighbor].split(",")
                    self.connect.click((int(x2)+int(x1))/2,(int(y2)+int(y1))/2)
                    logger.warning(f" 点击了 {neighbor} 坐标为 {x1,y1,x2,y2}")
                    if neighbor=="无限制": 
                        time.sleep(0.5)
                        self.connect.keyevent("4")
                    time.sleep(3.5)
                    isexit=True
            if not isexit:break
        return True #如果有弹窗 就继续检查 当检查不到弹窗的时候可以结束

    def StopGame(self):
        """终止游戏"""
        if self.PackageUrl == "":
            logger.info("以远程方式跑用例，不关")
            return
        try:
            if self.logcat!=None:
                self.logcat.stop_nowait()
                self.logcat=None
            self.connect.app_stop(self.PackageInfo["name"])
            return True
        except:
            logger.error(traceback.format_exc())
            return False

    def GetAllAPP(self):
        """获取设备所以应用程序"""
        return self.connect.list_packages()
    
    def GetAPPInfo(self):
        """获取应用信息"""
        return self.connect.app_info(self.PackageInfo["name"])
    
    def AppsIsRun(self):
        """应用是否正在运行"""
        cmds = ["ps | grep {}", "ps -A | grep {}"]
        for cmd in cmds:
            result = self.connect.shell(cmd.format(self.PackageInfo["name"]))
            if result:
                break
        if result:
            return result.split()[1]
        else:
            return None
    
    def ClickScreen(self,x,y,duration=0):
        """点击屏幕坐标"""

        self.connect.click(x,y)
        
    def SlideScreen(self,x,y,x1,x2,duration=0):
        """滑动屏幕"""
        self.connect.swipe(x,y,x1,x2,duration)

    def MoveAndScroll(self,x,y,distance):
        """移动的指定位置并点击"""
        #移动的不需要移动 直接点击就行
        self.connect.click(x,y)
    
    def GetScreenshot(self,file_path="",file_name=""):
        """获取截屏 返回路径"""
        dirname = ""
        if file_path == "":
            dirname = f"{config.DownloadScreenshotPath}"
        else:
            dirname = f'{config.DownloadFilePath}/{file_path}'
        if not os.path.exists(dirname):
            os.makedirs(dirname)
        ppaht = f'{dirname}/{int(time.time())}.png'
        if file_name:ppaht = f'{dirname}/{file_name}.png'
        try:
            self.connect.screenshot().save(ppaht)
            logger.info("截图 保存位置为"+ppaht)
            return ppaht
        except:
            logger.info("截图 失败")
            return ""
        
    
    def get_log_url(self,casename=""):
        if self.PackageUrl == "":
            logger.info("远程，不拉日志")
            return
        if self.logcat_file_path !="":
            return f"http://{util.get_ip()}/UAutoCacheFiles/GameLog/"+ urllib.parse.quote(os.path.basename(self.logcat_file_path))
        return ""
    
    def get_utrace_url(self,casename=""):
        "获取采集的utrace文件 URL"
        ProfilesPath=f"/storage/emulated/0/Android/data/{self.PackageInfo['name']}/files/UE4Game/EM/EM/Saved/Profiling"
        latestFile=None
        for fileitem in self.connect.sync.list(ProfilesPath):
            if ".utrace" in fileitem.path:
                if latestFile==None:latestFile=fileitem
                if fileitem.mtime>latestFile.mtime:latestFile=fileitem
        if latestFile==None:return ""
        print(latestFile.path)
        new_file_name=f"/{casename}-{self.DName}-{datetime.now().strftime('-%Y-%m-%d_%H-%M-%S')}.utrace"
        self.pull(ProfilesPath+"/"+latestFile.path,config.GameFilesPath+"/"+new_file_name)
        time.sleep(1)
        self.connect.remove(ProfilesPath+"/"+latestFile.path)
        return f"http://{util.get_ip()}/UAutoCacheFiles/GameFiles/"+ new_file_name
    
    def get_new_csv_file(self,file_path=""):
        "获取采集的csv文件"
        if ".csv" in file_path:
            file_name=os.path.basename(file_path)
            ProfilesPath=f"/storage/emulated/0/Android/data/{self.PackageInfo['name']}/files/UE4Game/EM/EM/Saved/Profiling/{file_name}"
            new_file_path=f"{config.GameFilesPath}/{self.DName}-{file_name}"
            self.pull(ProfilesPath,new_file_path)
            if os.path.exists(new_file_path):return new_file_path
        return ""
    
    def pull(self,src,dst=None):
        """获取文件
        src:设备内文件地址
        dst:将文件获取下来存放的位置
        """
        if dst==None:
            dst=config.GameFilesPath
        return self.connect.sync.pull(src, dst)

    def push(self,file_path,local_path):
        """推送文件
        file_path:文件地址
        local_path:推送到设备本地文件地址
        """
        logger.warning(f"推送文件:{file_path} 到设备:{local_path} 中")
        if not os.path.exists(file_path):
            logger.error("推送失败 文件不存在")
            return False
        self.connect.push(file_path,local_path)
        return True


    def Is_Recording(self) -> bool:
        return self.recording_process and self.recording_process.poll() is None
    
    def Start_Recording(self, file_path="",file_name="",quality="low"):
        """
        开始录屏
        """
        if self.Is_Recording():
            logger.info("存在录制，打断")
            self.Stop_Recording()
            time.sleep(2)

        dirname = f'{config.DownloadFilePath}/{file_path}'
        os.makedirs(dirname, exist_ok=True)
        
        timestamp = int(time.time())
        file = ""
        # 生成唯一文件名
        if file_name == "" :
            file = f"{dirname}/scrcpy_record_{timestamp}.mkv"
        else:
            file = f'{dirname}/{file_name}.mkv'

        bit_rate = "8m"
        if quality == "mid":
            bit_rate = "8m"
        elif quality == "high":
            bit_rate = "12m"
        # # scrcpy位置
        # scrcpy_path =f"{config.DownloadFilePath}/scrcpy-win64-v3.3.1/scrcpy-win64-v3.3.1/scrcpy.exe"
        # 构建scrcpy命令
        command = [
            config.SCRCPY_PATH,
            "-s", f"{self.Devices}",
            "--record", f"{file}",
            "--no-playback",  # 禁用显示
            "--no-window",
            "-b", bit_rate, # 码率
        ]
        # file = open("d:/output.txt","a")
        logger.info(command)
        self.recording_process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            start_new_session=True,  # 创建新会话组
            creationflags=subprocess.CREATE_NO_WINDOW
        )
        return file
        
    def Stop_Recording(self):
        """停止录制"""
        # https://github.com/Genymobile/scrcpy/pull/6244
        if self.Is_Recording():
            try:
                logger.info("尝试杀死录制进程")
                process = self.connect.shell("ps -A | grep -e 'app_process'").strip().split('\n')
                # print(process)
                if len(process) != 0:
                    for line in process:
                        lis = line.split()
                        # print(lis)
                        pid = lis[1]
                        self.connect.shell(f"kill {pid}")
                        return True
                # self.recording_process.send_signal(signal.CTRL_BREAK_EVENT)
                # time.sleep(1)
            except:
                logger.info("没有找到进程") 
        return False

    def file_exits(self,file_path,file_name):
        process = self.connect.shell(f"ls {file_path} | grep {file_name}")
        if process == file_name:
            return True
        else:
            return False
if __name__ == '__main__':
    AD = AndroidDevice("test", "JB6PPNKRGU8DTWYD", "",
                       PackageInfo={"name": "com.yingxiong.pan01", "activity": "com.epicgames.ue4.SplashActivity",
                                    "version": "1.0.0.1.2", "project": "EM", "branch": "20250422",
                                    "UE_branch": "release-ce20", "size": 1.46})
    AD.Initialization()
    # AD.Click_Install_pop()
    AD.StartGame(" -trace=log,counters,cpu,frame,bookmark,file,loadtime,gpu,rhicommands,rendercommands,object -statnamedevents -tracefile ")
    # print(AD.file_exits(file_name="EM",file_path="/storage/emulated/0/Android/data/com.yingxiong.pan01/files/UE4Game/"))

    # AD.StartGame(command=" -trace=log,counters,cpu,frame,bookmark,file,loadtime,gpu,rhicommands,rendercommands,object -statnamedevents -tracefile ")
    # AD.StopGame()
    # AD.ClosePopUpWindow()
    # print(1)
    # AD.StartGame("-trace=log -statnamedevents -tracefile")