import time,os,sys
import json
import requests
from loguru import logger
class StatRecord(object):
    def __init__(self,udriver):
        self.udriver=udriver
        self.isrunning=False
        self.filepath=""
        self.casename=""
        self.appversion=""
        # self.LabelData={}
        
    def Prepare(self,FrameInterval=5,Pitem=["Niagara"]):
        Pitem.insert(0,FrameInterval)
        self.udriver.captureStat(-1,Pitem)
        logger.info("初始化 采集")
        time.sleep(1)
        return True
    
    def Start(self):
        self.udriver.captureStat(1)
        logger.info("启动stat 采集")
        self.isrunning=True
        return True

    def Stop(self,case_name,AppVersion=0):
        self.casename=case_name
        self.appversion=AppVersion
        if self.isrunning:
            self.filepath=self.udriver.captureStat(0)
            return self.filepath
        else:
            False

    def Save(self,filepath):
        if os.path.exists(filepath):
            with open(filepath, 'rb') as file:
                data = {
                    "game_version":self.appversion,
                    "report_user": "UAUTO",
                    "info":self.casename,
                    "labelinfo":"{}"
                }
                response = requests.post("http://127.0.0.1:8101/upload_stat_report", files={'file': file},data=data).json()
                logger.info(response)
                if "id" in response["data"]:
                    return response["data"]["id"]
                return str(response["data"])
        else:
            return ""
    
    def add_label(self,label_names):
        logger.info("Stat添加label"+str(label_names))
        if type(label_names)==list:
            if len(label_names)==1:
                self.udriver.captureStat("AddLabel",label_names)
            if len(label_names)==2:
                self.udriver.captureStat("AddLabelAndCMD",label_names)
        elif type(label_names)==str:
            self.udriver.captureStat("AddLabel",[label_names])
        return True