"""
1. 负责设备的连接控制 
2. 任务的状态控制
3. 任务的进程管理

"""

import os,sys
import subprocess
import threading

import requests
from loguru import  logger
import config
import socket,time
import platform,json,traceback
from multiprocessing import Process,Lock,freeze_support
import RunTask,ctypes
from DeviceControl import Control
from DeviceControl import winUtils
from DeviceControl.idevice.utils.tunneld import run_tunneld
from utils import main_ui_test, FTP
import wget
from threading import Timer
from utils import pyfeishu
from utils.ios_tunnel import get_ios_devices,Tunnel

from utils.util import DownloadFile,Detect_the_device_info,clean_extra_pid_by_name
import psutil
from DeviceControl.idevice import idevice_api
import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)


lock=Lock()
fieshu=pyfeishu.FeiShubot(config.WebHook)


def get_contorller_task():
    """获取设备任务"""
    global Server_ERROR,RunTaskList,DeviceInfo
    if RunTaskList!={}:
        for i in list(RunTaskList.keys()):
            try:
                if not RunTaskList[i].is_alive():
                    RunTaskList.pop(i)
            except:
                logger.warning(i+"进程已经结束")
                RunTaskList.pop(i)
    try:
        taskinfolist=requests.get(f"{config.UAutoServer}/task_run/get_contorller_task").json()
    except :
        logger.warning("获取设备任务失败: "+traceback.format_exc())
        Server_ERROR=True 
        return False
    taskinfolist=taskinfolist["data"]
    if len(taskinfolist)>0:
        disk_free=Control.get_disk_free()
        if disk_free<=30:
            fieshu.send_text(f"{socket.gethostname()}{DeviceInfo['name']} 工作磁盘剩余 {str(disk_free)} 空间不足30G")
        logger.info("获取到的任务信息: ")
        logger.info(taskinfolist)
        for taskinfo in  taskinfolist:
            deviceinfo=taskinfo["device"]
            taskKey=f"{taskinfo['task_running_name']}_{taskinfo['task_running_id']}_{deviceinfo['id']}"
            if taskinfo["device"]["os"]!="PC":
                file_name:str = wget.filename_from_url(taskinfo["package_url"])
                file_name=file_name.replace(":","-")
                file_path=os.path.join(config.DownloadFilePath, file_name)
                if not os.path.exists(file_path):
                    try:
                        DownloadFile(taskinfo["package_url"])
                    except:
                        logger.error("包体下载失败")
                        fieshu.send_text(taskinfo["package_url"]+"包体下载失败:"+traceback.format_exc())
            if taskKey in RunTaskList:
                fieshu.send_text(f"{taskKey}_{deviceinfo['name']} 还未结束 但是重复收到了这个任务 需要等待之前的任务结束  存在的任务进程id为{RunTaskList[taskKey].pid}, 已强杀进程")
                tP:Process=RunTaskList[taskKey]
                tP.kill()
                time.sleep(5)
                if tP.is_alive():
                   fieshu.send_text(f"{taskKey}_{deviceinfo['name']} 进程id{tP.pid} 杀不掉")
                   continue

            TaskParamete={'device_id': deviceinfo["id"], 'device_name': deviceinfo["name"], 'device_s': deviceinfo["serial_id"], 'device_ip': deviceinfo["ip"], 'os': deviceinfo["os"], 'device_perf': deviceinfo["perf"],'control_type': deviceinfo["control_type"],'device_parameters':deviceinfo["parameters"],'project_id': taskinfo["project_id"], 
            'project_name': taskinfo["project_name"], "gitlab_url": taskinfo["gitlab_url"], 'feishu_token': taskinfo["feishu_token"],   'package_url': taskinfo["package_url"],  'name': taskinfo["task_running_name"], 'id': taskinfo["task_running_id"], 
            'parameters': taskinfo["task_parameters"], 'trigger_user': taskinfo["trigger_user"], 'package_info': taskinfo["package_info"],"is_server_task":True}
            logger.info(TaskParamete)
            runtask=RunTask.TaskRunProcess(TaskParamete)
            p=Process(target=runtask.begin_run_cases)
            # p.name = f"{taskinfo['task_running_name']}"
            p.start()
            logger.info(f"{taskKey}_{p.pid} 开始运行")
            RunTaskList[taskKey]=p
                

def heartbeat():
    """同步设备状态"""
    global Server_ERROR
    
    try:
        for item in get_ios_devices():
            if int(item["ProductVersion"].split(".")[0])>=17 and not config.is_run:
                tu=Tunnel()
                tu.start_tunnel()
                config.is_run=1
                break
        devices=Control.GetConnectedDevices()
        logger.info(f"{devices}-{threading.get_ident()}")
        ret=requests.post(f"{config.UAutoServer}/controlle/heartbeat",json= {"devices": devices},timeout=10).json()
        logger.info(ret["data"])
    except :
        logger.info(traceback.format_exc())
        logger.info("获取设备信息失败")
        Server_ERROR=True

def updata_control():
    global RunTaskList,isrunning
    vername=os.path.basename(os.getcwd())
    if not os.path.exists("version"):
        with open("version","w+") as f:
            f.write(vername)
    else:
        with open("version","r") as f:
            vername=f.read()
    qdqurl=requests.get("http://127.0.0.1:8101/common/get_control_url").json()["ToolUrl"]
    sversion = os.path.splitext(os.path.basename(qdqurl))[0]
    logger.info(f"本地版本{vername}, 服务端版本{sversion}")
    if vername!= sversion:
        logger.warning("版本不一致 更新",RunTaskList)
        if RunTaskList !={}:
            logger.info("有任务 等一会再更新控制端"+qdqurl)
            Timer(120, updata_control, ()).start()
            return "有任务 等一会再更新控制端"
        if os.path.exists(f"{config.DownloadFilePath}//update.exe"):
            os.remove(f"{config.DownloadFilePath}//update.exe")
        wget.download("http://127.0.0.1/UAutoControl/update.exe",out=config.DownloadFilePath,bar=None)
        unpack_path=os.path.join(os.path.abspath('..'),sversion)
        if os.path.exists(unpack_path):
            os.makedirs(unpack_path)
        subprocess.Popen(f"{config.DownloadFilePath}//update.exe {qdqurl} {unpack_path} {'notrun' if not isrunning else 'running' }", creationflags=subprocess.CREATE_NEW_CONSOLE)
        sys.exit(1)
    Timer(240, updata_control, ()).start()
    return "3分钟在检测一次"

DeviceInfo={}
isrunning=False
FTPserver=None
LastTime=0
def AgentRun():
    global isrunning,Server_ERROR,DeviceInfo,FTPserver,LastTime
    if isrunning:
        logger.info("服务端运行中")
        return
    isrunning=True
    if sys.platform=="win32":
        #检测设备是否注册到平台中
        DeviceInfo=Detect_the_device_info(ui)
        print(DeviceInfo)
    try:
        FTPserver=FTP.FTPThread()
        FTPserver.start()
        logger.info("FTPserver 开启成功")
    except:
        logger.warning("FTPserver 开启失败")   
    
    # 重置连接到服务器的设备连接状态
    try:
        requests.post(f"{config.UAutoServer}/controlle/reset_device_state").json()
        isrunning=True
    except:
        logger.error("服务器连接失败:"+traceback.format_exc())
        isrunning=False
        return

    logger.info(f"控制器 开始执行 ")
    while isrunning:
        time.sleep(2)
        heartbeat()
        get_contorller_task()
        # if LastTime - time.time()<=30: #这里有个bug 会触发连个线程
        #     return
        # LastTime=time.time()
        while Server_ERROR:
            try:
                ret=requests.head(config.UAutoServer)
                Server_ERROR=False
            except :
                logger.info("服务端还未恢复")
                time.sleep(10)
        # print("等待20s")
        time.sleep(60)
    logger.info("执行结束")
    isrunning=False
def AgentStop():
    global isrunning,FTPserver
    isrunning=False
    try:
        if FTPserver:
            FTPserver.stop()
            FTPserver=None
        if "id" in DeviceInfo:
            response = requests.get(f"{config.UAutoServer}/device/update_device_active", params={
                        "id": DeviceInfo["id"],
                        "active": 0
                    }).text
            logger.warning("释放设备"+response)
    except:
        logger.warning("任务终止失败"+traceback.format_exc())
    

def cquit():
    global FTPserver
    if FTPserver!=None:
        FTPserver.stop()

RunTaskList={}
Server_ERROR=False
FTPserver=None
gdevice=winUtils.WinUtils()
if __name__ == "__main__":
    vername=os.path.basename(os.getcwd())
    if vername == "UAutoTestFor01" or vername == "UAutoControl" or "-debug" in sys.argv  or "_" not in vername:
        config.DEBUG=True
        # 示例仓库不保存真实 Webhook；请通过本地配置或环境变量注入。
        config.WebHook=""

    if not config.DEBUG and not ctypes.windll.shell32.IsUserAnAdmin():
        logger.error("请使用管理员身份运行程序!!!!!")
        input("输入任意键 退出")
        sys.exit()
    freeze_support()
    #这里检查一下删一个任务的残留进程
    clean_extra_pid_by_name("UAutoControl.exe")
    logger.remove()
    t = time.localtime()
    logger.add(f'{config.DownloadFilePath}/logs/control_{t.tm_mon}_{t.tm_mday}.log',level="INFO")
    ui=main_ui_test.Main_UI(AgentRun,AgentStop,cquit)
    logger.add(ui.add_UAuto_log,format="{time:MM-DD HH:mm:ss} | {level} | {message}")
    try:logger.add(sys.stdout, level='INFO')
    except:pass
    logger.info(f"初始化成功 {sys.argv}")
    logger.info(f"设备的唯一ID为 {gdevice.get_Unique_id()}")
    run_tunneld()
    #检测更新
    if not config.DEBUG:
        updata_control()
    if "check" in sys.argv:
        print("没有问题")
        sys.exit()
    logger.info(config.UAutoServer)
    ui.run()
