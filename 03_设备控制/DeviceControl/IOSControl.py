import concurrent.futures
import concurrent
import contextlib
import socket
import subprocess
import threading
import urllib.request
from pathlib import Path
from urllib import parse
import cv2
import numpy as np
import requests
from DeviceControl.idevice.api import EnterableRemoteServiceDiscoveryService
from importlib.metadata import version
__version__ = version("pyimg4")
from DeviceControl.ControlBase import DeviceControlBase
import time
from loguru import logger
import wda
import config
from utils import util
import os,sys
from datetime import datetime
from  DeviceControl.idevice import idevice_api
from utils.ios_tunnel import  start_wda_thread

def normalize_path(path: str) -> str:
    # 把所有 / 和 \ 统一成单斜杠 \
    return os.path.normpath(path)



class IOSDevice(DeviceControlBase):
    def __init__(self,DeviceName="",Devices="",Device_IP="", Control_Type="",PackageUrl="",PackageInfo={}, DeviceID=0, Device_Parameters={}):
        super().__init__(DeviceName,Devices,Device_IP, Control_Type,PackageUrl,PackageInfo, DeviceID, Device_Parameters)
        wda.DEBUG = False
        self.Platform="IOS"
        self.Devices=Devices
        self.DeviceName=DeviceName
        wda.HTTP_TIMEOUT = 180.0
        wda.DEVICE_WAIT_TIMEOUT = 180.0
        self.wdaname = "com.panshen.wda"
        self.wdaconnect=""
        self.isRunSysLog=False
        self.local_port=9100
        self.is_recording=False
        self.fps=8
        self.frame_size = (1920,1080)
        self.log_file_path=""
        self.dev = idevice_api.Idevices(self.Devices)
    def __del__(self):
        try:
            self.isRunSysLog = False
            if self.wdaconnect:
                try:
                    self.wdaconnect.session.close()
                except Exception:
                    pass
                try:
                    self.wdaconnect.close()
                except Exception:
                    pass
        except Exception as e:
            pass
    def Initialization(self):
        try:
            logger.info("开始连接WDA")
            self.wdaconnect = wda.Client(f"http+usbmux://{self.Devices}:8100")
            logger.info("连接WDA成功")
            time.sleep(2)
        except:
            logger.info("连接WDA失败,尝试再次连接")
            try:
                with idevice_api.Idevices(self.Devices) as dev:
                    dev.launch(self.wdaname)
                logger.info("启动WDA成功")
                time.sleep(2)
                self.wdaconnect = wda.Client(f"http+usbmux://{self.Devices}:8100")
                time.sleep(5)
            except:
                logger.info("启动WDA失败")
                raise "WDA初始化失败检查"


    def GetDeviceIP(self):
        """获取设备ip"""
        def get_ip():
            try:
                with idevice_api.Idevices(self.Devices) as dev:
                    return str(dev.get_ip())
            except:
                return ""
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(get_ip)
            try:
                return future.result(timeout=5)
            except concurrent.futures.TimeoutError:
                return ""

    def GetDeviceState(self):
        """获取设备状态"""
        try:
            device_locked = self.wdaconnect.locked()
        except:
            self.Initialization()
            device_locked = self.wdaconnect.locked()
        return not device_locked
    def UnOrlockDevice(self, Islock: bool):
        """解锁设备/关闭设备"""
        if Islock:
            self.wdaconnect.lock()
        else:
            self.wdaconnect.unlock()
        time.sleep(0.5)
        return self.wdaconnect.locked() == Islock

    def Install_Package(self):
        """安装应用"""
        logger.info('Begin Install APK_IPA')
        packages=self.GetAllAPP()
        if self.PackageInfo["name"] in packages:
            if self.PackageInfo["version"] != self.GetAPPVersion():
                logger.info("包版本不一致!! 更新")
                self.UNInstall_Package(self.PackageInfo["name"])
            else:
                logger.info("包版本一致, 跳过安装")
                return True
        file_path=util.DownloadFile(self.PackageUrl)
        time.sleep(1)
        try:

            with idevice_api.Idevices(self.Devices) as dev:
                dev.install_app(file_path)
                self.ClosePopUpWindow()
            time.sleep(1)
        except:
            time.sleep(10)
            with idevice_api.Idevices(self.Devices) as dev:
                dev.install_app(file_path)

    def UNInstall_Package(self, bundle_id):
        """卸载应用"""
        with idevice_api.Idevices(self.Devices) as dev:
            return dev.uninstall_app(bundle_id)


    def StartGame(self,command=""):
        self.ClosePopUpWindow()
        """启动游戏"""
        if self.AppsIsRun():
            self.StopGame()
        self.isRunSysLog=True
        self.start_syslog()
        # 
        ucmdpath=f"{config.DownloadGameLogPath}/{self.DName}/ue4commandline.txt"
        if command != "":
            os.makedirs(os.path.dirname(ucmdpath), exist_ok=True)  # 自动创建目录
            with open(ucmdpath, "w") as f:
                f.write(command)
            self.push(ucmdpath, "/Documents/ue4commandline.txt")  # 推送文件过去
            time.sleep(1)
        self.wdaconnect.app_launch(self.PackageInfo["name"])
        time.sleep(10)
        if command!="":
            with idevice_api.Idevices(self.Devices) as dev:
                dev.rm(self.PackageInfo["name"],"/Documents/ue4commandline.txt")
        return self.AppsIsRun()

    def ClosePopUpWindow(self):
        """关闭弹窗"""
        try:
            for i in ["无线局域网与蜂窝网络","信任","允许","好","稍后","允许跟踪","OK","关闭"]:
                logger.info(f"点击弹窗:{i}")
                self.wdaconnect.alert.click_exists(i)
        except:
            logger.info(f"点击弹窗失败")
            pass

    def StopGame(self):
        """终止游戏"""
        if self.PackageUrl == "":
            logger.info("以远程方式跑用例，不关")
            return
        try:
            self.wdaconnect.app_stop(self.PackageInfo["name"])
            self.isRunSysLog=False
        except:
            with idevice_api.Idevices(self.Devices) as dev:
                return dev.kill_ipa(self.PackageInfo["name"])

    def StopApp(self,Packagename="com.panshen.wda"):
        """终止应用"""
        try:
            self.wdaconnect.app_stop(Packagename)
            self.isRunSysLog=False
        except:
            with idevice_api.Idevices(self.Devices) as dev:
                return dev.kill_ipa(Packagename)

    def GetAllAPP(self):
        """获取设备所有应用程序"""
        with idevice_api.Idevices(self.Devices) as dev:
            return dev.GetAllAPP()
    
    def GetAPPVersion(self):
        """获取app版本"""
        with idevice_api.Idevices(self.Devices) as dev:
            return dev.GetAPPVersion(self.PackageInfo["name"])

    def xcode(self):
        """获取app版本"""
        with idevice_api.Idevices(self.Devices) as dev:
            return dev.enable_developer_mode()


    def AppsIsRun(self):
        """应用是否正在运行"""
        app_state=self.wdaconnect.app_state(self.PackageInfo["name"])
        if app_state["value"] == 4:
            return True
        return False

    def ClickScreen(self, x, y, duration=0):
        """点击屏幕坐标"""
        self.wdaconnect.click(x, y)

    def SlideScreen(self, x, y, x1, x2, duration=0):
        """滑动屏幕"""
        self.wdaconnect.swipe(x, y, x1, x2, duration)

    def MoveAndScroll(self, x, y, distance):
        """移动的指定位置并点击"""
        self.wdaconnect.click(x, y)

    def GetScreenshot(self,file_path="",file_name=""):
        """获取截屏 返回路径"""
        dirname = ""
        if file_path == "":
            dirname = f"{config.DownloadScreenshotPath}"
        else:
            dirname = f'{config.DownloadFilePath}/{file_path}'
        if not os.path.exists(dirname):
            os.makedirs(dirname)
        ppaht = f"{dirname}/{int(time.time())}.png"
        if file_name:ppaht = f'{dirname}/{file_name}.png'
        try:
            self.wdaconnect.screenshot().save(ppaht)
            logger.info("截图 保存位置为: " + ppaht)
            return ppaht
        except:
            return ""
        
    def reboot(self):
        """重启设备,慎用可能会导致wda无法启动"""
        with idevice_api.Idevices(self.Devices) as dev:
            dev.reboot()


    def pull(self,src,dst,remove=False,local_rename=None):
        """获取文件
        src:设备内文件地址
        dst:将文件获取下来存放的位置
        remove:是否删除
        local_rename:重名名
        """
        with idevice_api.Idevices(self.Devices) as dev:
            dev.pull(self.PackageInfo["name"],dst,src,remove,local_rename)

    def push(self,file_path,device_path):
        """推送文件
        file_path:文件地址
        device_path:远程本地文件地址
        """
        with idevice_api.Idevices(self.Devices) as dev:
            dev.push(self.PackageInfo["name"], file_path, device_path)


    @util.async_fun
    def start_syslog(self):
        try:
            with idevice_api.Idevices(self.Devices) as dev:
                s=dev.syslog()
                self.log_file_path = f"{config.DownloadGameLogPath}/{self.DName}_{datetime.now().strftime('IOS-%Y-%m-%d_%H-%M-%S.log')}"
                try:
                    logger.info("收集log 开始")
                    with open(self.log_file_path, 'a') as f:
                        while self.isRunSysLog:
                            text = next(s)
                            f.write(text + '\n')
                            f.flush()
                    logger.info("收集log 结束")
                except (BrokenPipeError, IOError):
                    logger.info("收集log 失败")
                    devnull = os.open(os.devnull, os.O_WRONLY)
                    os.dup2(devnull, sys.stdout.fileno())
        except:
            pass
    def get_log_url(self,casename=""):
        if self.PackageUrl == "":
            logger.info("远程，不拉日志")
            return
        if self.log_file_path !="":
            return f"http://{util.get_ip()}/UAutoCacheFiles/GameLog/"+ parse.quote(os.path.basename(self.log_file_path))
        return ""
    
    def get_utrace_url(self,casename=""):
        "获取采集的utrace文件 URL"
        self.PackageInfo["name"]="com.hero.dna"
        ProfilesPath=f"/Library/EM/Saved/Profiling"
        with idevice_api.Idevices(self.Devices) as dev:
            files = dev.ls(self.PackageInfo["name"], ProfilesPath)
        latestFile=None
        for fileitem in files:
            print(fileitem)
            if ".utrace" in fileitem.name:
                if latestFile==None:latestFile=fileitem
                if fileitem.mtime>latestFile.mtime:latestFile=fileitem
        if latestFile==None:return ""
        new_file_name=f"{self.DeviceName}-{casename}-{datetime.now().strftime('-%Y-%m-%d_%H-%M-%S')}.utrace"
        self.pull(ProfilesPath+"/"+latestFile.name,config.GameFilesPath,remove=True,local_rename=new_file_name)
        return f"http://{util.get_ip()}/UAutoCacheFiles/GameFiles/"+ new_file_name
    
    def get_new_csv_file(self,file_path=""):
        "获取采集的csv文件"
        if ".csv" in file_path:
            file_name=os.path.basename(file_path)
            ProfilesPath=f"/Library/EM/Saved/Profiling"
            new_file_name=f"{self.DeviceName}-{file_name}"
            self.pull(ProfilesPath+"/"+file_name,config.GameFilesPath,remove=True,local_rename=new_file_name)
            return config.GameFilesPath+"/"+new_file_name
        else:
            return ""

    def start_relay(self):
        def get_free_port():
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.bind(('localhost', 0))
            _, port = sock.getsockname()
            sock.close()
            return port
        if self.local_port==9100:
            self.local_port = get_free_port()
            logger.info(f"转发端口至：{self.local_port}")

            self.dev.relay_start(local_port=self.local_port)
            return self.local_port
        else:
            return self.local_port


    def stop_relay(self):
        self.dev.relay_stop()
        time.sleep(2)
        return self.local_port

    def Is_Recording(self) -> bool:
        return self.is_recording

    def Start_Recording(self, file_path="", file_name="", quality="low"):
        """开始录制 MJPEG 流到 MP4 文件"""
        if self.is_recording:
            self.Stop_Recording()
            time.sleep(2)

        dirname = f'{config.DownloadFilePath}/{file_path}'
        os.makedirs(dirname, exist_ok=True)

        self.is_recording = True
        self._start_time = time.time()
        full_path = f"{config.DownloadFilePath}/{file_path}/{file_name}.mkv" if file_path else (
                    file_name or "output.mp4")
        full_path = normalize_path(full_path)

        # 保存当前文件路径到实例属性
        self._current_file = full_path

        print(full_path)
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        self._out = cv2.VideoWriter(full_path, fourcc, self.fps, self.frame_size)

        def record():
            stream = requests.get(f"http://127.0.0.1:{self.start_relay()}", stream=True)
            bytes_data = b""
            logger.info(f"开始录制到 {full_path}")
            while self.is_recording:
                for chunk in stream.iter_content(chunk_size=1024):
                    if not self.is_recording:
                        break
                    bytes_data += chunk
                    a = bytes_data.find(b'\xff\xd8')
                    b = bytes_data.find(b'\xff\xd9')
                    if a != -1 and b != -1:
                        jpg = bytes_data[a:b + 2]
                        bytes_data = bytes_data[b + 2:]
                        frame = cv2.imdecode(np.frombuffer(jpg, dtype=np.uint8), cv2.IMREAD_COLOR)
                        if frame is not None:
                            if frame.shape[1] != self.frame_size[0] or frame.shape[0] != self.frame_size[1]:
                                frame = cv2.resize(frame, self.frame_size)
                            self._out.write(frame)

        self._thread = threading.Thread(target=record, daemon=True)
        self._thread.start()
        return_path = f"{config.DownloadFilePath}/{file_path}/{file_name}.mp4"
        return return_path

    def Stop_Recording(self):
        """停止录制并自动转 MP4"""
        if not self.is_recording:
            logger.info("当前没有录制任务")
            return

        self.is_recording = False
        if self._thread:
            self._thread.join()
        if self._out:
            self._out.release()

        elapsed = time.time() - self._start_time
        current_file = getattr(self, "_current_file", None)

        if current_file and current_file.endswith(".mkv"):
            try:
                # 转成同名 MP4
                base = str(Path(current_file).with_suffix(""))
                mp4_file = f"{base}.mp4"
                cmd = [
                    config.FFMPEG_PATH,
                    "-y",
                    "-i", current_file,
                    "-c:v", "libx264",
                    "-pix_fmt", "yuv420p",
                    "-crf", "23",
                    "-r", "30",
                    mp4_file
                ]
                # logger.info(f"正在转码: {' '.join(cmd)}")
                subprocess.run(cmd, check=True ,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
                logger.info(f"转码完成文件: {mp4_file}")
                os.remove(current_file)
                current_file = mp4_file

            except Exception as e:
                logger.error(f"转码失败: {e}")

        logger.info(f"录制完成，文件: {current_file}, 用时: {elapsed:.2f} 秒")
        return f"{elapsed:.2f} 秒"

if __name__ == "__main__":
    AD = IOSDevice("test", "00008130-00045C3E266A001C", "",
                       PackageInfo={"name": "com.hero.dna", "activity": "com.hero.dna", "version": "1.0.0.401", "project": "EM", "size": 4.38},DeviceID="EXAMPLE-IOS-DEVICE-ID",PackageUrl="https://example.invalid/pan01/Packages/CN/IOS/Uauto_OBT11_Dev/Uauto_OBT11_Dev_385392_2025-12-12_11-32-54_1.1.5.1_dev_EM.ipa")

    # print(wda.Client(f"http+usbmux://00008130-00045C3E266A001C:8100").status())

    AD.Initialization()
    time.sleep(1)
    AD.StartGame()
    time.sleep(10)
    AD.StopGame()
    # print(AD.get_log_url())
    # AD.Install_Package()
    # for i in range(10):
    #     print(AD.Start_Recording(r"ScreenshotRecords/ipadmini6/b88bf520828711f0b95cfc3497b64881",f"V_17562155{i}1_TestDecalMap"))
    #     print("开始录屏")
    #     time.sleep(2)
    #     print("结束")
    # print(AD.Stop_Recording())
    # import cv2
    #
    # print(cv2.getBuildInformation())