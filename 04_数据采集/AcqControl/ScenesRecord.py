import time,os,sys
import json
import requests
from loguru import logger
class ScenesRecord(object):
    def __init__(self,udriver,dist=600):
        self.udriver=udriver
        self.dist=dist
        self.isrunning=False
        self.filepath=""
        self.casename=""
        self.appversion=""
        self.platform=self.udriver.platform
        if self.platform=="PC":self.platform="Win64"

    def Start(self):
        self.udriver.scenePerfCheck(1,self.dist)
        logger.info("启动stat 采集")
        self.isrunning=True
        return True
    
    def IsRunning(self):
        return self.udriver.scenePerfCheck(2)

    def Stop(self,case_name,AppVersion=0):
        self.casename=case_name
        self.appversion=AppVersion
        if self.isrunning:
            self.udriver.scenePerfCheck(-1)
            time.sleep(1)
            self.filepath=self.udriver.scenePerfCheck(2)
            return self.filepath
        else:
            ""
    def Save(self,filepath):
        if os.path.exists(filepath):
            with open(filepath, 'rb') as file:
                data = {
                    "game_version":self.appversion,
                    "report_user": "UAUTO",
                    "platform":self.platform,
                    "info":self.casename,
                    "interval":self.dist,
                    "sceneslinfo":"{}"
                }
                response = requests.post("http://127.0.0.1:8101/upload_scenes_report", files={'file': file},data=data).json()
                logger.info(response)
                if "id" in response["data"]:
                    return response["data"]["id"]
                return str(response["data"])
        else:
            return ""