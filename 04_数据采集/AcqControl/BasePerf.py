import socket,subprocess,os,json
import zerorpc,time
from loguru import logger
import utils.util as util
import requests
import config,psutil
from AcqControl import Autil

class PerfClient(object):
    def __init__(self, perf_path:str=None,port=None):
        self.perf_path = perf_path
        self.process = None
        self.RPC=None
        self.message_id = 0
        self.port = self.site_port(port)
        self.isrunning = False

    def Start(self):
        if not self.perf_path.endswith("exe"):
            self.perf_path=os.path.join(self.perf_path,"PerfTool.exe")
        cmd=[self.perf_path, "-BP" ,"1", "-port" ,str(self.port)]
        logger.info(f"启动 PerfTool.exe : {self.port}")
        cwd = os.path.split(self.perf_path)[0]
        print(cwd)
        for i in range(3):
            if not os.path.exists(self.perf_path):
                time.sleep(15)
                logger.warning("可能别的进程正在安装工具 等一会吧")
                continue
            break
        self.process = subprocess.Popen(cmd, cwd=cwd)
        time.sleep(3)
        self.RPC = zerorpc.Client(timeout=120,heartbeat=60)
        logger.info(f"连接 tcp://127.0.0.1:{self.port}")
        self.RPC.connect(f"tcp://127.0.0.1:{self.port}")
        self.isrunning=True
        return self.isrunning

    def Stop(self):
        self.send_message("disconnect_device")
        time.sleep(2)
        logger.info("停止 stop_rpc_server : ")
        self.send_message("stop_rpc_server")
        time.sleep(1)
        self.process.kill()
        self.isrunning=False

    def send_message(self,func,params={}):
        self.message_id += 1
        msg = json.dumps({"id": self.message_id, "func": func, "params":params})
        logger.info(f"PerfClient: {self.message_id} {func} 发送: {params}")

        data=self.RPC.on_message(msg)
        logger.info(f"PerfClient: {self.message_id} {func} 接收: {data}")
        data=json.loads(data)
        return data

    def site_port(self,port=None):
        if port==None:
            port=Autil.get_free_port()
        return port
class BasePerf(object):
    def __init__(self,perf_path=None,device="localhost"):
        self.device=device
        self.pid=0
        if perf_path==None:
            self.downloadPerfTool()
        else:
            self.perf_path=perf_path
        print(self.perf_path)
        self.Perf=PerfClient(self.perf_path)
        self.app_info={}

    def downloadPerfTool(self):
        ret=requests.get("http://127.0.0.1:8101/common/get_perftool_url")
        PackageUrl=ret.json()["ToolUrl"]
        filename=os.path.splitext(os.path.basename(PackageUrl))[0]
        if filename not in os.listdir(config.DownloadFilePath):
            result=util.DownloadFile(PackageUrl)
            if result !="":
                FilePPath=util.UnZipFile(result)
                if FilePPath:
                    logger.info("解压完成: "+FilePPath)
                    #添加应用到防火墙
                    os.system(f'netsh advfirewall firewall add rule name="PerfTool" dir=in action=allow program="{FilePPath}\\PerfTool.exe"')
                else:
                    logger.error("包体解压失败")
            else:
                logger.error("包体下载失败")
                raise Exception("包体下载失败")
            logger.info("包体安装完成")
        self.perf_path=os.path.join(config.DownloadFilePath,filename,"PerfTool.exe")
        logger.info(f"程序路径：{self.perf_path}")
        #清理3天前的缓存文件
        Autil.del_file(os.path.join(config.DownloadFilePath,filename,"cachedata"))
    
    def PreInit(self):
        #启动RPC 连接
        self.Perf.Start()
        time.sleep(2)
        #连接设备
        self.Perf.send_message("get_connected_devices")
        time.sleep(1)
        retdata=self.Perf.send_message("connect_device",self.device)
        try:
            if "error" in retdata["result"]:
                logger.error("连接设备失败: "+retdata["result"])
                return False
        except:
            pass
        time.sleep(2)
        device_info=self.Perf.send_message("get_device_info")
        logger.info(device_info)
        return True

    def Start(self,package="EM.exe"):
        app_list=[]
        for it in range(3):
            app_list=self.Perf.send_message("get_app_list")
            if app_list["result"]!=[]:
                break
            else:
                if it==2:
                    raise Exception("获取应用列表失败 可能是perfserver挂了/应用没有获取应用列表权限")
                time.sleep(2)
        if package=="EM.exe":
            self.pid=Autil.get_pid(package)
        for appitem in app_list["result"]:
            if appitem["packageName"]==package:
                if package=="EM.exe" and self.pid!=0 :
                    if str(self.pid) in appitem["label"]:
                        self.app_info=appitem
                        break
                else:
                    self.app_info=appitem
                    break
        if self.app_info=={}:raise Exception("应用不存在")
        self.Perf.send_message("select_app",self.app_info)
        self.Perf.send_message("start_perf")
        time.sleep(2)

    def Stop(self,save,case_name):
        self.Perf.send_message("stop_perf")
        filename=None
        if save:
            filename=self.Perf.send_message("save_report",case_name)["result"]
        logger.info(filename)
        time.sleep(1)
        self.Perf.Stop()
        return filename
    
    def Kill(self):
        return self.Perf.Stop()
    
    def add_label(self,label_name):
        if self.Perf.isrunning:
            ret=self.Perf.send_message("add_label",label_name)["result"]
            logger.info(ret)
            return ret
        return False

if __name__ == "__main__":
    # Client=PerfClient("D:\CodeRepository\PerfTool\dist\PerTool\PerfTool.exe")
    # Client.Start()
    # data=Client.send_message("get_connected_devices")
    # print(data)
    # time.sleep(50)
    # Client.Stop()
    # data=BasePerf()
    pass
