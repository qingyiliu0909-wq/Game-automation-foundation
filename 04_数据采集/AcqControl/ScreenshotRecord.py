import time,os,uuid
import json
import config
import requests
import threading
from PIL import Image
from DeviceControl.ControlBase import DeviceControlBase
from loguru import logger
from utils import util
from uedriver import AltrunUnrealDriver
from DeviceControl.AndroidControl import AndroidDevice
from AcqControl import AcqPerf
import uedriver

class ScreenshotRecord(object):
    def __init__(self,udriver,DeviceControl,project_name,case_name,constant=False):
        self.udriver=udriver
        self.isrunning=False
        self.platform = udriver.platform
        self.index = 1
        self.constant = constant
        self.case_name = case_name
        self.projetc_name = project_name
        self.stop_screen_event = threading.Event()
        self.DeviceControl:DeviceControlBase=DeviceControl
        self.files = []
        self.uid = uuid.uuid1().hex


    def prepare(self):
        # 检查录屏工具有无下载
        if os.path.exists(config.FFMPEG_PATH) and os.path.exists(config.SCRCPY_PATH):
            logger.info("录屏工具都存在...")
            return 
        logger.info("开始下载录屏工具...")
        file_path=util.DownloadFile(config.SCREEN_TOOL_URL)
        if file_path != "":
            ziped_path = util.UnZipFile(file_path)
            if ziped_path!="":
                logger.info("screen_tool解压成功")
            else:
                raise Exception("screen_tool解压失败")
        else:
            raise Exception("远程screen_tool不存在")
       
    def Start(self):
        # logger.info("启动 截图")
        return True
    
    def get_screenshot(self,label_name=""):
        save_path = f'ScreenshotRecords/{self.DeviceControl.DName}/{self.uid}'
        if label_name:label_name=f"{int(time.time())}_{label_name}"
        img = self.DeviceControl.GetScreenshot(save_path,label_name)
        self.compress_img(img)
        self.files.append(os.path.basename(img))

    def compress_img(self,file_path,quality=60):
        img = Image.open(file_path)
        img = img.convert('RGB')
        img.save(file_path, format='JPEG', quality=quality)

    def Stop(self):
        # self.stop_screen_event.set()
        self.DeviceControl.Stop_Recording()
        return self.Save()
    
    def start_screenrecord(self,label_name="",quality="low"):
        save_path = f"ScreenshotRecords/{self.DeviceControl.DName}/{self.uid}"
        if label_name:label_name=f"{int(time.time())}_{label_name}"
        record = self.DeviceControl.Start_Recording(save_path,label_name,quality)
        if record != None:
            self.files.append(os.path.basename(record))

    def Save(self):
        if len(self.files) == 0:
            logger.warning("未开始采集or采集到的数据为空，不上传")
            return ""
        device_parameters = json.loads(self.DeviceControl.Device_Parameters)
        save_ip = ""
        if self.DeviceControl.Platform != "Win64":
            save_ip = "10.18.18.206"
        else:
            save_ip = self.DeviceControl.Device_IP
        info = {
                "root":f"http://{save_ip}/UAutoCacheFiles/ScreenshotRecords/{self.DeviceControl.DName}/{self.uid}",
                "files":self.files
        } 
        # for file in self.files:
        #     # 上传到服务器
        #     # params = {
        #     #     'dirname': f'compatible_screenshot/{self.uid}',
        #     # }
        #     # files = {
        #     #     'files': (os.path.basename(file),open(f'{file}', 'rb')),
        #     # }
        #     # res = requests.post('http://127.0.0.1:8101/common/upload_file', params=params, files=files).json()
        #     # print(res)
        #     info["files"].append(os.path.basename(file))
        # res = {"data":"1"}
        package = {
            'package_url':self.DeviceControl.PackageUrl,
            'package_info':self.DeviceControl.PackageInfo
        }
        if "cpu_type" in device_parameters:
            cpu_name = device_parameters["cpu_type"]
        else:
            cpu_name = "没有填"

        if "gpu_type" in device_parameters:
            gpu_name = device_parameters["gpu_type"]
        else:
            gpu_name = "没有填"

        json_data = {
            'report_user': 'UAuto',
            'info':json.dumps(info),
            'platform': self.platform,
            'task_name': self.case_name,
            'device_name': self.DeviceControl.DName,
            'device_id':self.DeviceControl.DID,
            'project':self.projetc_name,
            'package':json.dumps(package),
            'cpu_name':cpu_name,
            'gpu_name':gpu_name
        }
        logger.info(json_data)
        # res = ""
        res = requests.post('http://127.0.0.1:8101/upload_screenshot_report',json=json_data).json()
        if res != "":
            return res['data']
        else:
            return ""

    def add_label(self,label_name="",quality="low"):
        if self.constant and self.index != 1:
            return
        self.get_screenshot(label_name=label_name)
        self.start_screenrecord(label_name=label_name,quality=quality)
        self.index+=1
        return True




if __name__ == '__main__':
    p = json.dumps({"os_type": "android", "os": "15", "cpu_type": "mt6899", "cpu_arch": "arm64-v8a", "cpu_core_num": "8", "cpu_freq": "300000MHz-2100000MHz\n300000MHz-2100000MHz\n300000MHz-2100000MHz\n300000MHz-2100000MHz\n400000MHz-3000000MHz\n400000MHz-3000000MHz\n400000MHz-3000000MHz\n1000000MHz-3250000MHz", "gpu_type": "ARM Mali-G720 MC7", "opengl": "OpenGL ES 3.2 v1.r49p1-03bet0.bedd3f0c1eaa833146818ccc820a3501", "gpu_freq": "null", "resolution": "1220x2712", "ram_size": "11.0 GB", "swap": "12287 MB", "root": "No", "device_model": "24129RT7CC"})

    ad=AndroidDevice("测试", "WKP7DY45PZKZRS5D","127.0.0.1",PackageUrl="https://example.invalid/pan01/Packages/CN/Android_ASTC/Android_0826_Dev/Android_0826_Dev_325380_2025-09-09_03-32-45_0.1.10.1_dev_EM.apk",
                                   PackageInfo = {"name": "com.yingxiong.pan01", "activity": "com.epicgames.ue4.GameActivity", "version": "0.1.10.1", "project": "EM", "branch": "20250826", "UE_branch": "release-ce23", "size": 2.65}, 
                                   DeviceID=1047,
                                   Device_Parameters=p)
    ad.Initialization()
    # ad.StartGame()
    
    udriver=uedriver.AltrunUnrealDriver("测试","",TCP_IP='127.0.0.1')

    acq = AcqPerf.AcqControl(udriver,"图形兼容","TestProjectUE",{"collection":["screenshot"]},DeviceControl=ad,bot="",appName="",device="",device_perf=3)
    acq.init_capture()
    acq.run_capture()
    p = {}
    p["add_label"]=acq.add_label
    # pages.graphics_compatible.AutoRun(udriver,p)
    # pages.RunMap.RunMap_BingHuCheng.BeforeRun(udriver,p)
    # pages.RunMap.RunMap_BingHuCheng.AutoRun(udriver,p)
    acq.stop_capture()