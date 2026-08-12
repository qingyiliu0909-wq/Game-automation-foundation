import time,os,sys,uuid
sys.path.append("D:/CodeRepository/UAutoTestFor01")
from loguru import logger
from AcqControl import Autil
import threading
import psutil,traceback
from PIL import ImageGrab, Image
import config,json,requests

class MemoryRecord(object):
    def __init__(self,device_id="localhost"):
        self.device_id=device_id
        self.pid=0
        self.isrunning=False
        self.cachepath=None
        self.index=0
        self.t=None
        self.casename=""


    def Record(self):
        self.isrunning=True
        self.file.write("[")
        while self.isrunning:
            st=int(time.time())
            
            private=self.get_memory()
            ppath=self.cachepath+"/"+str(st)+"_"+str(int(private))+"MB.jpeg"
            info={
                "time":st,
                "private":private,
                "rss":self.get_working_set(),
                "screenshot":self.get_screenshot(ppath)
            }
            logger.info(info)
            if self.index==0:self.file.write(json.dumps(info))
            else:self.file.write(","+json.dumps(info))
            self.file.flush()
            self.index+=1
            time.sleep(10)
        self.file.write(',{"casename":"'+self.casename+'"}]')
        self.file.close
        logger.info("收集结束")

    """表示进程的专用内存大小（专用内存是指进程独占的内存区域）"""
    def get_memory(self):
        try:
            return self._Process.memory_info().private / 1024 /1024
        except Exception as e:
            traceback.print_exc()
            return 0

    """进程实际使用的物理内存（包括共享库占用的内存），但不包括被换出到交换区的内存"""
    def get_working_set(self):
        try:
            return self._Process.memory_info().rss / 1024 /1024
        except Exception as e:
            traceback.print_exc()
            return 0
        
    def get_screenshot(self,name):
        image = ImageGrab.grab()
        width, height = image.size
        image = image.resize((int(width/2),int(height/2)), Image.LANCZOS )
        image.save(name, format="JPEG")
        return name
        
    def PreInit(self):
        #创建一个唯一的文件夹存放数据 避免重复
        for i in range(3):
            self.cachepath=os.path.join(config.DownloadFilePath,str(uuid.uuid4()))
            if not os.path.exists(self.cachepath):
                os.makedirs(self.cachepath)
                break
        #把采集到的数据存放到文件中 避免因为程序问题导致数据丢失
        file_path=os.path.join(self.cachepath,"data.json")
        self.file=open(file_path,"w+")
        self.t = threading.Thread(target=self.Record,name="内存记录线程")
        logger.info("准备完成")
        logger.info("文件地址为: "+ self.cachepath)
        return True

    def Start(self,package="EM.exe"):
        self.pid=Autil.get_pid(package)
        if self.pid==0:
            raise ProcessLookupError(package+" 进程找不到")
        self._Process = psutil.Process(self.pid)
        self.t.start()
        time.sleep(2)
        logger.info("启动")
        return True

    def Stop(self,case_name):
        self.casename=case_name
        self.isrunning=False
        self.t.join()
        return self.cachepath
    
    def update_memory(self,udriver,parameters:dict,info):
        logger.info(info+"截取内存")
        url = "http://127.0.0.1:8101/upload_memreport"
        if udriver.platform =="PC":
            path = udriver.memReport()
            with open(path, 'rb') as file:
                data = {
                    "game_version": parameters["version"],
                    "report_user": "UAUTO",
                    "info": info
                }
                requests.post(url, files={'file': file}, data=data)
        elif udriver.platform =="ios": # 安卓不能用 ios无法pull文件
            # IOSControl:IOSDevice=parameters["device_control"]
            path = udriver.memReport()
            # IOSControl.pull(path)
            pass
        elif udriver.platform =="android": # 安卓不能用 ios无法pull文件
            # AndroidControl:AndroidDevice=parameters["device_control"]
            # path = udriver.memReport()
            # AndroidControl.pull(path)
            pass
if __name__ == "__main__":
    Record=MemoryRecord()
    Record.PreInit()
    Record.Start()
    time.sleep(10)
    file=Record.Stop("内存测试")
    logger.info(file)
    logger.info("完成")