import traceback
import time 
from loguru import logger
from AcqControl import BasePerf,MemoryRecord, StatRecord,ScenesRecord,ScreenshotRecord
from DeviceControl.ControlBase import DeviceControlBase


class AcqControl(object):
    def __init__(self,udriver,case_name,project_name,parameters,bot,appName,device,DeviceControl,device_perf):
        self.udriver=udriver
        self.case_name=case_name
        self.appName=appName
        self.parameters:dict=parameters
        self.bot=bot
        self.project_name = project_name
        self.performance = {}
        self.report_data = {}
        self.device=device
        self.device_perf=device_perf
        self.DeviceControl:DeviceControlBase=DeviceControl

   #初始化采集
    def init_capture(self):
        logger.info("初始化采集")
        try:
            # 开始采集
            if "collection" in self.parameters.keys():
                #TODO 采集项目实例化
                if "perfbase" in self.parameters["collection"]:
                    self.performance["perfbase"] = BasePerf.BasePerf(device=self.device)
                    self.performance["perfbase"].PreInit()
                    logger.info("perfbase 初始化完成")
                if "memoryrecord" in self.parameters["collection"]:
                    self.performance["memoryrecord"] = MemoryRecord.MemoryRecord()
                    self.performance["memoryrecord"].PreInit()
                    logger.info("memoryrecord 初始化完成")
                if "statrecord" in self.parameters["collection"]:
                    self.performance["statrecord"] = StatRecord.StatRecord(self.udriver)
                    self.performance["statrecord"].Prepare()
                    logger.info("statrecord 初始化完成")
                if "scenesrecord" in self.parameters["collection"]:
                    sdist=600
                    if "sdist" in self.parameters:
                        sdist=self.parameters["sdist"]
                    self.performance["scenesrecord"] = ScenesRecord.ScenesRecord(self.udriver,sdist)
                    logger.info("scenesrecord 初始化完成")
                if "perfdeep" in self.parameters["collection"]:
                    if self.udriver.platform =="PC":
                        self.udriver.GM("Trace.Stop")
                    logger.info("perfdeep 初始化完成")
                if "screenshot" in self.parameters["collection"]:
                    self.performance["screenshot"] = ScreenshotRecord.ScreenshotRecord(self.udriver,self.DeviceControl,self.project_name,self.case_name, constant="constant" in self.parameters)
                    self.performance["screenshot"].prepare()
                    logger.info("screenshot 初始化完成")
                
            else:
                self.parameters["collection"]=[]
            # 其他采集

        except Exception as e:
            logger.error(traceback.format_exc())
            raise Exception(self.device+f": 采集初始化失败")
    #开始采集
    def run_capture(self):
        logger.info("开始采集流程")
        try:
            if "perfbase" in self.performance.keys():
                self.performance["perfbase"].Start(self.appName)
            if "memoryrecord" in self.parameters["collection"]:
                self.performance["memoryrecord"].Start()
                self.performance["memoryrecord"].update_memory(self.udriver,self.DeviceControl.PackageInfo,f"{self.case_name+'_'+self.DeviceControl.DName}开始")
            if "statrecord" in self.parameters["collection"]:
                self.performance["statrecord"].Start()
            if "scenesrecord" in self.parameters["collection"]:
                self.performance["scenesrecord"].Start()
            if "perfdeep" in self.parameters["collection"]:
                if self.udriver.platform =="PC":
                    self.udriver.GM("Trace.Start")
            if "screenshot" in self.parameters["collection"]:
                self.performance["screenshot"].Start()
            return True
        except Exception as e:
            logger.error(traceback.format_exc())
            # raise Exception(f"采集开始失败")
            return False
    
    # 停止采集
    def stop_capture(self,save=True,AppVersion="0"):
        logger.info(f"停止采集流程: {save}")
        try:
            if "perfbase" in self.performance.keys():
                Quality="无"
                if self.device_perf==0:Quality="VeryLow"
                elif self.device_perf==1:Quality="Low"
                elif self.device_perf==2:Quality="Middle"
                elif self.device_perf==3:Quality="High"
                ret=self.performance["perfbase"].Stop(save,{"CaseName":self.case_name,"AppVersion":AppVersion,"Scenes":self.case_name,"Quality":Quality})
                if save:self.report_data["perfbase"]=ret["data"]["id"]
            if "memoryrecord" in self.performance.keys():
                self.performance["memoryrecord"].update_memory(self.udriver,self.DeviceControl.PackageInfo,f"{self.case_name+'_'+self.DeviceControl.DName}结束")
                ret=self.performance["memoryrecord"].Stop(self.case_name+"_"+self.DeviceControl.DName)
                self.report_data["memoryrecord"]=ret
            if "statrecord" in self.performance.keys():
                ret_file_path=self.performance["statrecord"].Stop(self.case_name+"_"+self.DeviceControl.DName,AppVersion)
                loc_file_path=self.DeviceControl.get_new_csv_file(ret_file_path)
                self.report_data["statrecord"]=self.performance["statrecord"].Save(loc_file_path)
            if "scenesrecord" in self.performance.keys():
                ret_file_path=self.performance["scenesrecord"].Stop(self.case_name+"_"+self.DeviceControl.DName,AppVersion)
                loc_file_path=self.DeviceControl.get_new_csv_file(ret_file_path)
                self.report_data["scenesrecord"]=self.performance["scenesrecord"].Save(loc_file_path)
            if "screenshot" in self.parameters["collection"]:
                ret = self.performance["screenshot"].Stop()
                self.report_data["screenshot"] = ret['id']
            if "perfdeep" in self.parameters["collection"]:
                self.udriver.GM("Trace.Stop")
            if "uploadpso" in self.parameters["collection"]:
                self.udriver.GM("r.ShaderPipelineCache.Upload")
            return True
        except Exception as e:
            logger.error(traceback.format_exc())
            return False
        
    # 停止采集
    def clean_capture(self):
        logger.info(f"停止采集流程:")
        try:
            if "perfbase" in self.performance.keys():
                self.performance["perfbase"].Kill()
            return True
        except Exception as e:
            logger.error(traceback.format_exc())
            return False

    def add_label(self,label_name):
        try:
            if "perfbase" in self.performance.keys():
                self.performance["perfbase"].add_label(label_name)
            if "statrecord" in self.performance.keys():
                self.performance["statrecord"].add_label(label_name)
            if "screenshot" in self.performance.keys():
                self.performance["screenshot"].add_label(label_name)
            else:
                logger.info("标签: "+label_name)

        except Exception as e:
            logger.error("添加标签失败"+traceback.format_exc())

