import re
import requests
import time,json,os

import config
from DeviceControl.PCControl import del_file
import uedriver
import traceback
from config import  ROOT_DIR, UAutoServer,DownloadFilePath
from DeviceControl.Control import *
from loguru import logger
import importlib
import queue
from utils import git_lab
from AcqControl import AcqPerf
from utils.case_status import *
from utils import util
from utils.util import RedictStdout


pyfeishubot=None
class TaskRunProcess(object):

    #需要注意 init是在主进程进行的
    def __init__(self,TaskParameter):
        global pyfeishubot
        self.is_server_task= TaskParameter["is_server_task"]  if "is_server_task" in TaskParameter else True 
        
        self.parameter=TaskParameter
        self.task_name=TaskParameter["name"]
        self.task_id=TaskParameter["id"]
        self.task_parameters=TaskParameter["parameters"]
        self.trigger_user=TaskParameter["trigger_user"]
        
        self.project_id=TaskParameter["project_id"]
        self.project_ame=TaskParameter["project_name"]
        self.feishu_token = TaskParameter["feishu_token"]
        self.gitlab_url = TaskParameter["gitlab_url"]
        self.platform = GetDeviceOSEnumType(TaskParameter["os"])  # 设备系统
        if self.is_server_task:
            if self.platform ==DeviceOS.PC:
                self.bot=pyfeishubot if pyfeishubot!=None else pyfeishu.FeiShubot(config.WebHook)
            elif self.platform ==DeviceOS.Android:
                self.bot = pyfeishubot if pyfeishubot != None else pyfeishu.FeiShubot(config.AndroidWebHook)
            elif self.platform == DeviceOS.IOS:
                self.bot = pyfeishubot if pyfeishubot != None else pyfeishu.FeiShubot(config.IOSWebHook)
        else:
            self.bot=pyfeishu.FeiShubot(webhook=None)
        # self.bot=pyfeishubot if pyfeishubot!=None else pyfeishu.FeiShubot(self.feishu_token)

        self.device_name=TaskParameter["device_name"]
        self.device_id = int(TaskParameter["device_id"])
        self.device_s = TaskParameter["device_s"] #设备号
        self.device_ip = TaskParameter["device_ip"] #设备ip
        self.device_perf = TaskParameter["device_perf"] #设备性能

        self.control_type = TaskParameter["control_type"]
        self.device_parameters = TaskParameter["device_parameters"] # 设备参数信息

        self.logpath=f"{DownloadFilePath}/logs/{self.task_id}-{self.task_name}/{self.device_name}"

        self.package_url = TaskParameter["package_url"]
        self.package_name =  os.path.basename(TaskParameter["package_url"])
        if TaskParameter["package_info"]!="":
            self.package_info =json.loads(TaskParameter["package_info"])
        self.case_status = None #案例状态

        self.DeviceControl:PCDevice=None
        if  "branch" not in self.package_info:self.package_info["branch"]="trunk"
        self.branch="main" if self.package_info["branch"]=="trunk" else self.package_info["branch"]
        self.command=""
        #运行时用例参数
        self.task_use_case_id=0
        self.use_case_info={}
        self.skip_login = False if not "skip_login" in TaskParameter else TaskParameter["skip_login"]

        #重定向输出
        self.std=None

        # 是否是ip直连任务
        self.is_local_task = TaskParameter["is_local_task"] if "is_local_task" in TaskParameter  else False

    def Pre_execution_detection(self):
        try:
            self.task_parameters=json.loads(self.task_parameters)
            # 如果是直连任务，初始化设备控制器的父类
            if self.is_local_task:
                self.DeviceControl = DeviceControlBase(self.device_name,self.device_s,self.device_ip,self.control_type,self.package_url,self.package_info,self.device_id, self.device_parameters)
                return
        except:
            logger.warning("任务参数序列化失败: ", self.task_parameters)
            self.bot.send_text(f"{self.device_name} {self.task_name} {self.task_parameters} 任务参数序列化失败")
            self.task_parameters={}
        #清理设备磁盘
        del_file(DownloadFilePath,"_EM")
        #初始化设备控制
        self.DeviceControl:DeviceControlBase=GetDeviceControl(self.platform,self.device_name, self.device_s,self.device_ip,self.control_type,self.package_url,self.package_info, self.device_id,self.device_parameters)
        self.DeviceControl.Initialization()
        #检查设备IP是否准确
       
        rdevice_ip=self.DeviceControl.Check_IP()
        if rdevice_ip and rdevice_ip!=self.device_ip:
            self.bot.send_text(f"{self.device_name} 设备IP 由{self.device_ip} 变更为{rdevice_ip}")
            self.device_ip=rdevice_ip
 
        #TODO 游戏装包是否完成, 
        if not self.DeviceControl.GetDeviceState():
            self.bot.send_text(f"{self.device_name} 设备锁屏了")
        if self.is_server_task:
            ret=requests.get(f"{UAutoServer}/task_run/task_state",params={"device_id":self.device_id,"task_running_id":self.task_id}).json()
            logger.info(f"初始化完成 开始执行任务 一共有{ret['data'][0]}个案例")
            self.bot.send_text(f"{self.device_name} {self.task_name} 任务开始")

    # run 入口
    def begin_run_cases(self,CaseList:list=[]):
        try:
            # 整理准备的参数 准备环境
            self.Set_Log()
            self.Pre_execution_detection()
            if self.package_url != "":
                self.DeviceControl.Install_Package()
        except:
            logger.error(traceback.format_exc())
            if self.std!=None:
                self.std.restore()
            self.bot.send_text(f"{self.device_name} {self.task_name} 任务准备失败:{traceback.format_exc()}")
            return False

        try:
            while True:
                # region 循环获取案例信息

                #两种获取案例方式:
                if self.is_server_task:#会从服务端获取任务执行
                    response = requests.get(f"{UAutoServer}/task_run/get_next_case", params={
                        "task_running_id": self.task_id,
                        "device_id": self.device_id
                    })
                else: # 通过任务参数进行执行
                    if len(CaseList) > 0:
                        casename=CaseList.pop()
                        print(casename)
                        response = requests.get(f"{UAutoServer}/case/get_case_by_name", params={
                            "name": casename,
                        })
                        logger.info(response.content)
        
                    else:
                        break
                logger.info("get_next_case 获取到案例",response.content.decode("utf-8"))
                self.use_case_info=json.loads(response.content)["data"]
                if not self.is_server_task:
                    self.use_case_info['caseinfo'] = json.loads(response.content)["data"]
                # endregion

                # 当返回空所有案例已完成，退出主体
                if self.use_case_info == None or self.use_case_info == {}:
                    break

                # region 开始运行案例
                # 更新脚本
                self.Update_code()
                self.task_use_case_id= self.use_case_info["id"]
                # 执行案例
           
                self.run_use_case(self.use_case_info["caseinfo"])

                # 案例结束休息
                time.sleep(10)

                if not self.DeviceControl.DeviceIsOnline():
                    self.bot.send_text(f"{self.device_name} {self.device_s} 设备离线了 请处理(任务已经强制终止)")
                    break
                # endregion
            #TODO 这里需要做一个接口 获取任务运行的结果概述 发送到群里
            self.bot.send_text(f"{self.device_name} 任务结束")
            logger.info("任务结束")
            
        except:
            self.bot.send_img(self.DeviceControl.GetScreenshot())#截图返回
            self.bot.send_text(f"{self.device_name} {self.device_s} 任务出错: "+traceback.format_exc())
            logger.error("任务出错了:"+traceback.format_exc())
            response = requests.get(f"{UAutoServer}/device/freed", params={"device_id": self.device_id}) #释放设备
            self.DeviceControl.StopGame()
                
            
        self.std.restore()

    def run_use_case(self,case_info):
        """
        执行单个案例
        """
        logger.info(f"开始执行{case_info['name']}")
        self.bot.send_text(f"{self.device_name} 开始执行 {case_info['name']}")
        self.report_data={}
        self.case_status = CaseStatusManage(self.task_use_case_id,self.bot,case_info["execute_time_out"],self.device_name+"-"+str(self.device_id),self.device_id,case_info["name"],case_info["id"],self.logpath)
        #初始化案例参数
        self.case_parameters = self.init_case_run_parameters()
        # 动态导入脚本
        before_runs,case_run,gset_uedriver=self.import_pages_module()
        if before_runs==[] and case_run==[]:
            self.case_status.upload_status(self.report_data)#上报失败了
            self.bot.send_text(f"{self.device_name} 执行 {case_info['name']}失败: 数据配置错误")
            return False
        
        for execute_i in range(case_info["attempt_times"]):
            #启动游戏
            excinfo=""
            self.AppearCrash=False
            self.CrashScreenshot=""
            self.case_status.refresh()
            def CrashCallback():
                self.CrashScreenshot=self.DeviceControl.GetScreenshot()
                self.AppearCrash=True
            if self.is_local_task or self.DeviceControl.StartGame(self.command):
                try:
                    # region 开始执行案例脚本
                    for i in range(3):
                        try:
                            udriver = uedriver.AltrunUnrealDriver(self.device_s, self.platform.name, self.device_ip)
                            break
                        except:
                            if i>=2:raise Exception("游戏没有安装自动化插件 或者游戏闪退/卡死了 自动化服务连接失败")
                            logger.warning("游戏可能还是没有启动 再等一会")
                            time.sleep(15) 
                    self.DeviceControl.ClosePopUpWindow()
                    # 案例状态控制
                    if self.is_server_task:
                        self.case_status.StartUp(udriver,CrashCallback,self.case_parameters)
                    
                    #给脚本全局一个udriver控制
                    gset_uedriver(udriver)

                    #TODO 初始化采集
                    ds=self.device_s
                    pname=self.package_info["name"]
                    if self.platform == DeviceOS.PC:
                        pname=self.DeviceControl.Game_Activity
                        ds="localhost"
                    self.AcqPerf=AcqPerf.AcqControl(udriver,case_info["name"],self.project_ame,self.case_parameters,self.bot,pname,ds,self.DeviceControl,self.device_perf)
                    self.AcqPerf.init_capture()
                    self.case_parameters["add_label"]=self.AcqPerf.add_label

                    #游戏置顶
                    if self.platform == DeviceOS.PC:
                        self.DeviceControl.GameOnTop()

                    #执行前置任务
                    for before_run in before_runs:
                        try:
                            self.DeviceControl.ClosePopUpWindow()
                            if self.skip_login and "login" in before_run['module'].__name__:
                                logger.info("跳过登录")
                                continue
                            logger.info(f"{self.device_s} 案例前操作开始 {before_run['module'].__name__} {before_run['func']}")
                            before_run["module"].__getattribute__(before_run["func"])(udriver, self.case_parameters)
                        except Exception as e:
                            logger.error("案例前操作失败:"+str(e))
                            time.sleep(5)
                            self.case_status.case_fail()  
                            self.AcqPerf.clean_capture()
                            raise InterruptedError("案例前操作失败") 
                        
                    # 开始采集
                    if not self.AcqPerf.run_capture():raise Exception(f"采集开始失败")

                    #游戏置顶
                    if self.platform==DeviceOS.PC:
                        self.DeviceControl.GameOnTop()
                    interim_case_name=self.case_parameters["name"]
                    for auto_run in case_run:
                        try:
                            self.DeviceControl.ClosePopUpWindow()
                            logger.info(f"{self.device_s} 案例主体开始 {auto_run['module'].__name__} {auto_run['func']}")
                            auto_run["module"].__getattribute__(auto_run["func"])(udriver, self.case_parameters)                   
                        except Exception as e:
                            excinfo=traceback.format_exc()
                            logger.error("案例执行失败"+excinfo) 
                            time.sleep(5)
                            if "失败" not in self.case_parameters["name"]:
                                interim_case_name+="(失败)"
                            self.case_status.case_fail()                     
                    if interim_case_name!=self.AcqPerf.case_name:
                        logger.warning("修改了案例名称"+interim_case_name)
                        self.AcqPerf.case_name=interim_case_name
                    #TODO 上传采集数据控制
                    time.sleep(2)
                    self.AcqPerf.stop_capture(save=True,AppVersion=self.package_info["version"])
                    self.report_data=self.AcqPerf.report_data
                    #等待15秒
                    time.sleep(10)
                    try:udriver.stop()
                    except:logger.warning("udriver停止失败:")

                    try:
                        if self.AppearCrash:
                            time.sleep(3)
                            clipboard_data = util.get_clipboard_data()
                            logger.error("出现了崩溃")
                            logger.info(clipboard_data)
                            excinfo+="出现了崩溃: "+clipboard_data
                            util.empty_clipboard_data()
                    except:
                        logger.error("崩溃信息捕获失败了")

                    Message="" #发送的消息体
                    if self.case_status.status!=CaseStatus.RUNNING:
                        self.bot.send_img(self.CrashScreenshot if self.CrashScreenshot!="" else self.DeviceControl.GetScreenshot())#截图返回
                        self.DeviceControl.StopGame()
                        titlename=f"执行失败：\n{excinfo} "
                        if self.case_status.status==CaseStatus.CANCEL:titlename=f"用例取消：\n "
                        elif self.case_status.status==CaseStatus.TIMEOUT:titlename=f"用例超时：\n "
                        Message=f"{self.device_name}_{case_info['name']} {titlename} \n {self.DeviceControl.get_log_url(self.AcqPerf.case_name)} \n"
                    else:
                        self.case_status.case_success()
                        self.DeviceControl.StopGame()
                        Message=f"{self.device_name} 执行成功 {self.AcqPerf.case_name}"

                    # region 发送消息通知 
                    if "perfdeep" in self.task_parameters["collection"] or "perfbase" in self.report_data:
                        if "perfbase" in self.report_data:
                            self.bot.send_text(Message,self.AcqPerf.case_name,"http://127.0.0.1:8898/#/perfkey/ReportInfo?id="+self.report_data["perfbase"])
                        if  "perfdeep" in self.task_parameters["collection"]: 
                            self.report_data["perfdeep"]=self.DeviceControl.get_utrace_url(self.AcqPerf.case_name)
                            self.bot.send_text(f"{self.device_name} Trace文件",self.AcqPerf.case_name,self.report_data["perfdeep"])
                    else:
                        self.bot.send_text(Message) #保底通知(如果没有采集数据)
                    # endregion
                    if self.case_status.status==CaseStatus.SUCCESS:break
                # endregion
                except Exception as e:
                    if self.AppearCrash:
                        time.sleep(3)
                        clipboard_data = util.get_clipboard_data()
                        logger.error("出现了崩溃")
                        logger.info(clipboard_data)
                        excinfo+="出现了崩溃: "+clipboard_data
                        util.empty_clipboard_data()
                    else:
                        excinfo+=traceback.format_exc()
                    try:
                        excinfo+=self.DeviceControl.get_log_url(case_info['name'])
                        self.AcqPerf.stop_capture(save=False,AppVersion=self.package_info["version"])
                    except:pass
                    logger.error(f"第{execute_i}次 案例执行失败")
                    self.bot.send_img(self.CrashScreenshot if self.CrashScreenshot!="" else self.DeviceControl.GetScreenshot())#截图返回
                    self.bot.send_text(f"{self.device_name}_{case_info['name']} :\n{excinfo}")
                    time.sleep(10)
            else:
                self.bot.send_text(f"{self.device_name}-{self.device_s} 游戏启动失败或设备掉线")
                logger.error(f"第{execute_i}次 游戏启动失败或设备掉线")
                self.case_status.case_fail()

        self.case_status.upload_status(self.report_data)

        #上传日志url地址
        self.case_status.upload_log(self.DeviceControl.get_log_url(self.AcqPerf.case_name))
        #保底 退出游戏
        self.DeviceControl.StopGame()

    """整理案例执行所需要的数据"""
    def init_case_run_parameters(self):
        parameters = {"account":{}}
        self.command=""
        case_info=self.use_case_info["caseinfo"]
        # 参数优先级: 任务参数 < 案例参数 < 用例参数
        # 任务参数
        parameters["task_id"]=self.task_id
        if self.task_parameters != None and self.task_parameters !={}:
            for key in self.task_parameters.keys():
                if "collection" ==key :
                    if "perfdeep" in self.task_parameters["collection"]:
                        if self.platform == DeviceOS.PC:
                            self.command+=" -trace=log,memory,counters,cpu,frame,bookmark,file,loadtime,gpu,rhicommands,rendercommands,object -statnamedevents  -tracefile "
                        elif self.platform == DeviceOS.Android:
                            self.command+=" -trace=log,counters,cpu,frame,bookmark,file,loadtime,gpu,rhicommands,rendercommands,object -statnamedevents -tracefile "
                        elif self.platform == DeviceOS.IOS:
                            self.command+=" -trace=log,memory,counters,cpu,frame,bookmark,file,loadtime,gpu,rhicommands,rendercommands,object -statnamedevents -tracefile "
                    if "uploadpso" in self.task_parameters["collection"]:
                        parameters["ForcedQuality"] = 1
                elif "collection" ==key and "stompmalloc" in self.task_parameters["collection"]:#内存检查
                    self.command+=" -stompmalloc"
                elif "command" == key:
                    self.command+=self.task_parameters[key]
                parameters[key]=self.task_parameters[key]
        
        # 案例信息
        parameters["name"] = case_info["name"]
        if case_info["parameters"] != None :
            case_info["parameters"]=json.loads(case_info["parameters"])
            if case_info["parameters"] !={}:
                for key in case_info["parameters"].keys():
                    parameters[key]=case_info["parameters"][key]
                

        # 用例参数
        if self.is_server_task:
            parameters["use_case_id"]=self.use_case_info["id"]
            UC_parameters={}
            if self.use_case_info["parameters"]!="" and self.use_case_info["parameters"]!=None:
                try:
                    UC_parameters=json.loads(self.use_case_info["parameters"])
                except:
                    logger.warning("案例参数序列化失败: ", self.use_case_info["parameters"])
                    self.bot.send_text(f"{self.device_name}-{self.device_s} 案例参数序列化失败(json格式): {self.use_case_info['parameters']}")
            if UC_parameters != None and UC_parameters !={}:
                for key in UC_parameters.keys():
                    parameters[key] = UC_parameters[key]
        else:
            # 本地任务参数中的cycles, account 优先级高一点
            if "cycles" in self.task_parameters:
                parameters["cycles"]  = int(self.task_parameters["cycles"])
            if "account" in self.task_parameters:
                parameters["account"] = self.task_parameters["account"]

        
        parameters["case_id"] = case_info["id"]
        #传入飞书
        parameters["feishu_bot"] = self.bot
        #设备名称
        parameters["device_name"] = self.device_name

        parameters["device_ip"] = self.device_ip
        parameters["device_id"] = self.device_id

        parameters["device_s"] = self.device_s
        if self.platform == DeviceOS.PC:
            parameters["game_path"] = self.DeviceControl.GamePath

        parameters["device_control"] = self.DeviceControl

        parameters["package_version"] = self.package_info["version"]

        parameters["package_url"] = self.package_url

        parameters["device_perf"] = self.device_perf

        parameters["wait_team_sync"]=print
        if case_info["execute_machine_count"] > 1:
            #同步方法
            parameters["wait_team_sync"] = self.case_status.wait_team_sync

        return parameters
        
    #动态导入案例模块
    def import_pages_module(self):
        importlib.invalidate_caches()
        # 案例需要导入模块
        auto_runs = []
        before_runs = []
        if self.case_parameters != None :       
            # 这里需要重新导入一些库
            def _get_module_load(name):
                modules=[]
                if name not in self.case_parameters.keys():return modules
                for i,run_case_fun in enumerate(self.case_parameters[name]):
                    file_path:str = run_case_fun["file_path"]
                    if file_path.endswith(".py"):file_path=file_path[:-3]
                    try:
                        modules.append( {
                            "module": importlib.import_module(file_path.replace("/", ".")),
                            "func": self.case_parameters[name][i]["func"]
                        })
                    except:
                        logger.error(traceback.format_exc())
                        self.bot.send_text(f"{self.device_name}-{self.device_s} 案例参数有问题 请核查{file_path}")
                return modules
            try:
                auto_runs = _get_module_load("auto_run")
                before_runs = _get_module_load("before_run")
            except:
                logger.error(traceback.format_exc())
                auto_runs = []
                before_runs = []
            if auto_runs ==[]:logger.error("案例信息不正确, 请核实")
        else:
            logger.error("案例信息不正确, 请核实")
        set_uedriver=print
        try:
            module=importlib.import_module("pages.Common.game_control")
            set_uedriver=module.set_uedriver
        except:
            logger.error("导入设置全局uedriver 方法失败了")
        return before_runs, auto_runs,set_uedriver
    
    def Set_Log(self):
        self.std=RedictStdout()
        process_id = os.getpid()
        if self.is_server_task:
            logger.remove()
        if re.search(r'[<>:"/\\|?*]', self.task_name) or re.search(r'[<>:"/\\|?*]', self.device_name):
            self.bot.send_text(f"{self.device_name} {self.task_name}信息中包含非法字符<>:\"/\\|?*")
            self.logpath=f"{DownloadFilePath}/logs/临时的文件夹"
        self.record_id=logger.add(f"{self.logpath}/TaskLog.log",level="INFO")
        logger.info(f"任务进程id为: {process_id}")

    def Update_code(self):
        if "-skipUpdateCode" in sys.argv: 
            logger.info("以不更新代码方式启动控制端") 
            return
        obj = git_lab.GitLab()
        Project=git_lab.GitLabProject(obj.getProjectByName("UAutoTestFor01"),self.branch)
        dirname="pages"
        if config.DEBUG: dirname="pages_test"
        if Project.pullCode(ROOT_DIR,dirname):
            logger.warning("开始清理导入缓存模块")
            for modeitem in list(sys.modules.keys()):# 这里清除一下pages的库的导入缓存
                if dirname in modeitem:del sys.modules[modeitem]
        logger.info("更新代码完成")



