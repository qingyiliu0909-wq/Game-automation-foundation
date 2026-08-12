from urllib import parse
from DeviceControl.ControlBase import DeviceControlBase
from loguru import logger
import wmi
import os,json
import time
import shutil,traceback
import win32com.client
import win32con
import win32gui
import wget,socket
from utils import util
import config
import shutil
from datetime import datetime
import keyboard,mouse
from PIL import ImageGrab
import threading
import win32con,win32gui, win32print
import subprocess

def del_file(file_dir,filter="",day=7):
    """清理三天前的文件"""
    if not os.path.exists(file_dir):return
    t=time.time()-86400*day
    for itme in os.listdir(file_dir):
        filepath=os.path.join(file_dir,itme)
        filetime= os.path.getmtime(filepath)
        if filetime<=t and filter in itme:
            #删除三天前的文件
            logger.info("removedirs",filepath)
            try:
                if os.path.isfile(filepath):
                    os.remove(filepath)
                else:
                    shutil.rmtree(filepath)
            except:
                logger.warning(traceback.format_exc())

class PCDevice(DeviceControlBase):
    def __init__(self, DeviceName,devices,device_ip, Control_Type,PackageUrl,PackageInfo={},deviceid=0,Device_Parameters={}):
        super().__init__(DeviceName, devices,device_ip, Control_Type,PackageUrl,PackageInfo, deviceid,Device_Parameters)
        self.hwnd=0
        self.Platform="Win64"
        self.width, self.height = ImageGrab.grab().size
        self.stop_event = threading.Event()
        self.recording_process = None
        self.game_project=self.PackageInfo["project"]#/EM

    def Initialization(self):
        # 包名和游戏名 暂且认为是相同的
        # self.GameName=self.PackageInfo["name"] #EM.exe 这个是窗口的名称 EM 会用中文
        self.Game_Activity=self.PackageInfo["activity"] #EM.exe/EM-Win64-Shipping.exe
        if self.PackageInfo["project"]=="EM":
            self.GameName="二重螺旋"#EM 使用中文名称
        else:
            self.GameName = self.game_project
            

    def GetDeviceState(self)->bool: 
        """获取设备状态"""
        for _i in range(2):
            result=win32gui.GetForegroundWindow()
            if result!=0:
                return True
            time.sleep(1)
        return False
    
    def UnOrlockDevice(self,Islock:bool): 
        """解锁设备/关闭设备"""
        logger.warning("PC不支持解锁设备 需要手动")
        return True

    def flushed_game_activity(self,FilePPath):
        if os.path.exists(f"{FilePPath}\\{self.game_project}\\Binaries\\Win64"):
            for item in os.listdir(f"{FilePPath}\\{self.game_project}\\Binaries\\Win64"):
                if self.game_project in item and "exe" in item:
                    self.Game_Activity=item
                    break
        else:
            logger.error("获取game_activity 失败了 路径不对")
            
    def Install_Package(self):
        """安装应用"""
        if self.PackageUrl.startswith("http://"):
        # https://example.invalid/pan01/Packages/CN/PCNoEditor/banshu/20230802_2023-10-30_19:33:54_0.10.0_EM.7z
            file_name:str = wget.filename_from_url(self.PackageUrl)
            # ? * : " < > \ / | 不能作为文件名
            file_name=file_name.replace(":","-")
            FilePPath=os.path.splitext(os.path.join(config.DownloadFilePath,file_name))[0]

            logger.info(FilePPath)
            exePPath=os.path.join(FilePPath,self.PackageInfo["name"])
            if  os.path.exists(exePPath):
                logger.info("包体已存在： "+exePPath)
                self.flushed_game_activity(FilePPath)
            else:
                result=util.DownloadFile(self.PackageUrl)
                if result !="":
                    FilePPath=util.UnZipFile(result)
                    self.flushed_game_activity(FilePPath)
                    if FilePPath:
                        logger.info("解压完成: "+FilePPath)
                        #添加应用到防火墙
                        os.system(f'netsh advfirewall firewall add rule name="{self.game_project}" dir=in action=allow program="{FilePPath}\\{self.game_project}\\Binaries\\Win64\\{self.Game_Activity}"')
                    else:
                        logger.error("包体解压失败")
                        raise Exception("包体解压失败")
                else:
                    logger.error("包体下载失败")
                    raise Exception("包体下载失败")
                logger.info("包体安装完成")
            self.GamePath=FilePPath
        else:
            if not os.path.exists(self.PackageUrl):raise Exception("本地传入路径不存在")
            self.GamePath = self.PackageUrl
        return self.GamePath

    def UNInstall_Package(self):
        """删除应用"""
        self.StopGame()
        shutil.rmtree(self.GamePath)
        return os.path.exists(self.GamePath)


    def StartGame(self,command=""):
        if self.PackageUrl == "":
            time.sleep(3)
            return True
        for _ in range(2):
            if self.AppsIsRun():
                logger.warning("游戏已经提前启动....!")
                self.StopGame()
                time.sleep(3)
            
            if not os.path.exists( os.path.join(self.GamePath,self.PackageInfo["name"])): raise FileNotFoundError()
            cmdstr=self.GamePath[0:2]+" & cd " +self.GamePath+ " & start " +self.PackageInfo["name"] +command
            logger.warning("执行指令:"+cmdstr)
            os.system(cmdstr)
            time.sleep(5)
            self.ClosePopUpWindow()
            time.sleep(5)
            for i in range(3):
                if self.AppsIsRun():
                    logger.warning("游戏启动成功....!")
                    return True
                time.sleep(5)
            logger.error("游戏启动失败,再次尝试....!")
                
        return False

    def ClosePopUpWindow(self):
        """关闭弹窗"""
        f=win32gui.FindWindow("#32770","打开文件 - 安全警告")
        print(f)
        if f!=0:
            win32gui.SetForegroundWindow(f)
            bu=win32gui.FindWindowEx(f,None,"Button","打开此文件前总是询问(&W)")
            win32gui.PostMessage(bu,win32con.WM_LBUTTONDOWN, win32con.MK_LBUTTON, 0)
            time.sleep(0.5)
            win32gui.SendMessage(bu, win32con.WM_LBUTTONUP, win32con.MK_LBUTTON, 0)
            time.sleep(0.5)
            bu=win32gui.FindWindowEx(f,None,"Button","运行(&R)")

            logger.warning("打开此文件前总是询问 点击 运行")
            time.sleep(1)
            win32gui.PostMessage(bu, win32con.WM_LBUTTONDOWN, win32con.MK_LBUTTON, 0)
            win32gui.PostMessage(bu, win32con.WM_LBUTTONUP, win32con.MK_LBUTTON, 0)
        time.sleep(3)
        f=win32gui.FindWindow("#32770","PC 安全中心警报")
        print(f)
        if f!=0:
            bu=win32gui.FindWindowEx(f,None,"Button","允许访问(&A)")
            time.sleep(1)
            win32gui.PostMessage(bu, win32con.WM_LBUTTONDOWN, win32con.MK_LBUTTON, 0)
            win32gui.PostMessage(bu, win32con.WM_LBUTTONUP, win32con.MK_LBUTTON, 0)
            logger.warning("PC 安全中心警报 点击允许访问")
        time.sleep(2)
        f=win32gui.FindWindow("Shell_SystemDialog","Windows 安全中心")
        print(f)
        if f!=0:
            bu=win32gui.FindWindowEx(f,None,"Button","允许(&A)")
            time.sleep(1)
            win32gui.PostMessage(f, win32con.WM_LBUTTONDOWN, win32con.MK_LBUTTON, 0)
            win32gui.PostMessage(f, win32con.WM_LBUTTONUP, win32con.MK_LBUTTON, 0)
            logger.warning("PC 安全中心警报 点击允许访问")

    def StopGame(self):
        if self.PackageUrl == "":
            logger.info("以远程方式跑用例，不关")
            return
        if self.AppsIsRun():
            self.keyboard_control("alt+F4")
            time.sleep(2)
        if self.AppsIsRun():
            time.sleep(15)
            logger.warning("alt+F4 没有杀掉进程 直接kill掉")
            cmd=f"taskkill /f /t /im {self.PackageInfo['name']}"
            logger.warning(cmd)
            os.system(cmd) #关闭游戏相关进程
        time.sleep(3)
        logger.info("关闭游戏")

    def GetAllAPP(self):
        pass

    def get_all_window(self):
        hWndList = []
        def winEnumHandler(hwnd, hWndList):
            if win32gui.IsWindowVisible(hwnd):
                hWndList.append(hwnd)
        win32gui.EnumWindows(winEnumHandler, hWndList) 
        
        return hWndList
    
    def keyboard_control(self,hotkey):
        logger.warning(hotkey)
        if self.hwnd !=0:
            #设置焦点
            try:win32gui.SetForegroundWindow(self.hwnd)
            except:pass
            keyboard.send(hotkey)
            return True
        return False

    def AppsIsRun(self):
        hWndList = self.get_all_window()      
        for hwnd in hWndList:
            title = win32gui.GetWindowText(hwnd)
            if len(title) > 0 and ":\\" not in title :
                if  self.GameName in title:
                    self.title=title
                    self.hwnd=hwnd
                    return True
        return False
    def ClickScreen(self,x,y,ClickType=1,duration=0):
        """点击屏幕
        ClickType 1:left,2:middle,3:right
        duration:持续时间
        """
        if x==0 and y==0:
            return False
        if ClickType==1:
            ClickType="left"
        elif ClickType==2:
            ClickType="middle"
        elif ClickType==3:
            ClickType="right"
        time.sleep(0.2)
        mouse.move(x,y)
        mouse.press(ClickType)
        time.sleep(duration)
        mouse.release(ClickType)

    def SlideScreen(self,x,y,x1,x2,duration=0):

        mouse.move(x,y)
        time.sleep(0.2)
        mouse.press("left")
        mouse.move(x1,x2,duration=duration)
        mouse.release("left")
        logger.info(f"鼠标滑屏 {x,y,x1,x2}")


    def MoveAndScroll(self,x,y,delta,distance):
        """移动的指定位置并滚动"""
        mouse.move(x,y)
        time.sleep(0.5)
        mouse.wheel(delta,distance)
        time.sleep(1)
        logger.info(f"鼠标 移动并滚动 {x,y,distance}")
   
    def GameOnTop(self):
        """置顶游戏"""
        try:
            shell = win32com.client.Dispatch("WScript.Shell") 
            shell.SendKeys('%')
            # 置顶（高亮）
            win32gui.SetForegroundWindow(self.hwnd)
            logger.info("游戏置顶")
        except:
            logger.error("游戏置顶失败")

    def GetScreenshot(self,file_path="",file_name=""):
        dirname = ""
        if file_path == "":
            dirname = f"{config.DownloadScreenshotPath}"
        else:
            dirname = f'{config.DownloadFilePath}/{file_path}'
        if not os.path.exists(dirname):
            os.makedirs(dirname)
        img_name=f"{dirname}/{int(time.time())}.png"
        if file_name:img_name = f'{dirname}/{file_name}.png'
        img = ImageGrab.grab()
        img.save(img_name)
        return img_name
    
    

    def get_log_url(self,casename=""):
        if self.PackageUrl == "":
            logger.info("远程，不拉日志")
            return
        logpath=os.path.join(self.GamePath,f"{self.game_project}/Saved/Logs")
        new_file_list = sorted(os.listdir(logpath), key=lambda file: os.path.getctime(os.path.join(logpath, file)))
        newfilename = casename+datetime.now().strftime('-%Y-%m-%d_%H-%M-%S.log')
        newfilename=newfilename.replace(":","-").replace("：","-")
        try:
            if new_file_list!=[]:
                shutil.copyfile(os.path.join(self.GamePath,f"{self.game_project}/Saved/Logs",new_file_list[0]), os.path.join(config.DownloadGameLogPath,newfilename) )
                return f"http://{util.get_ip()}/UAutoCacheFiles/GameLog/{parse.quote(newfilename)}"
        except:
            pass
        return newfilename
    
    def get_utrace_url(self,casename=""):
        "获取采集的utrace文件 URL"
        ProfilingPath=os.path.join(self.GamePath,f"{self.game_project}\\Saved\\Profiling")
        file_Path = ProfilingPath+"\\"+ sorted(os.listdir(ProfilingPath), key=lambda file: os.path.getctime(os.path.join(ProfilingPath, file)),reverse=True)[0]
        new_file_path=ProfilingPath+f"\\{casename}-{self.DName}-{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.utrace"
        os.rename(file_Path,new_file_path)
        new_file_path=new_file_path.replace("\\","/")
        return  f"http://{util.get_ip()}/UAutoCacheFiles/"+new_file_path.split("UAutoCacheFiles/")[-1]
    
    def get_new_csv_file(self,file_path=""):
        "获取采集的csv文件"
        if os.path.exists(file_path):return file_path
        return  ""
    
    @classmethod
    def get_device_GPU(self):
        """获取设备GPU型号"""
        w = wmi.WMI()
        for xk in w.Win32_VideoController():
            if not( "UHD Graphics 630"  in xk.name or "Microsoft" in xk.name):
                d =  xk.name
        return d.split("GTX ")[-1].split("RTX ")[-1]
    
    @classmethod  
    def del_file(self,file_dir,filter="",day=3):
        """获取三天前的时间戳"""
        if not os.path.exists(file_dir):return
        t=time.time()-86400*day
        for itme in os.listdir(file_dir):
            filepath=os.path.join(file_dir,itme)
            filetime= os.path.getmtime(filepath)
            if filetime<=t and filter in itme:
                #删除三天前的文件
                logger.info("removedirs",filepath)
                try:
                    shutil.rmtree(filepath)
                except:
                    logger.warning(traceback.format_exc())


    def get_real_screen_resolution(self):
        hDC = win32gui.GetDC(0)
        width = win32print.GetDeviceCaps(hDC, win32con.DESKTOPHORZRES)
        height = win32print.GetDeviceCaps(hDC, win32con.DESKTOPVERTRES)
        return f"{width}x{height}"


    def Is_Recording(self) -> bool:
        return  self.recording_process and self.recording_process.poll() is None
    
    def Start_Recording(self, file_path="",file_name="",quality="low"):
        """
        开始录屏
        """
        if self.Is_Recording():
            self.Stop_Recording()
        
        dirname = f'{config.DownloadFilePath}/{file_path}'
        os.makedirs(dirname, exist_ok=True)
        
        timestamp = int(time.time())
        file = ""
        # 生成唯一文件名
        if file_name == "" :
            file = f"{dirname}/record_{timestamp}.mp4"
        else:
            file = f'{dirname}/{file_name}.mp4'
        size=self.get_real_screen_resolution()

        command = [config.FFMPEG_PATH,
                "-f","gdigrab","-framerate","15","-offset_x","0","-offset_y","0","-video_size",size,"-i","desktop", #录制视频设置
                "-f","dshow","-i","audio=virtual-audio-capturer",#录制音频设置
                "-preset","ultrafast","-crf","25", #编码设置
                "-c:v","libx264","-c:a","copy",
                "-pix_fmt","yuv420p", #兼容本地显示的编码格式
                "-b:v","1500k",
                "-y", #是否覆盖
                file#保存文件
        ]
        logger.info(" ".join(command))
        self.recording_process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            stdin=subprocess.PIPE,
            creationflags=subprocess.CREATE_NO_WINDOW
        )
        return file

    def Stop_Recording(self):
        self.recording_process.stdin.write(b'q')
        time.sleep(2)
        try:
            stdout, stderr = self.recording_process.communicate(timeout=5)
            logger.info(f"进程已结束，返回值: {self.recording_process.returncode}")
            if stdout:logger.info(f"标准输出: {stdout}")
            if stderr:logger.info(f"标准错误: {stderr}")
        except subprocess.TimeoutExpired:
            logger.info("进程没有在指定时间内结束，强制终止...")
            self.recording_process.kill()
            stdout, stderr = self.recording_process.communicate()
            logger.info(f"进程已被强制终止")
