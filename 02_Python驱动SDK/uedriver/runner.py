import json
import os
import socket
import time
from loguru import logger
from uedriver.mouse_control import *
from uedriver.commands import *

BUFFER_SIZE = 1024

class AltrunUnrealDriver(object):

    def __init__(self, driver_s,  platform, TCP_IP='127.0.0.1',TCP_PORT=13000, timeout=60,request_separator=';',request_end='&',device_id="",log_flag=False):
        self.TCP_PORT = TCP_PORT
        self.request_separator=request_separator
        self.request_end=request_end
        self.log_flag=log_flag
        self.driver_s=driver_s
        self.connect = False
        self.platform=platform
        self.debug_handler = None


        while timeout > 0:
            try:
                self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.socket.connect((TCP_IP, TCP_PORT))
                self.socket.settimeout(timeout)
                logger.warning("Socket Connect Success")
                time.sleep(1)
                getPluginVersion(self.socket, self.request_separator, self.request_end).execute()
                self.connect = True
                break
            except Exception as e:
                logger.error(e)
                logger.error('AltUnrealServer not running on port ' + str(self.TCP_PORT) +
                      ', retrying (timing out in ' + str(timeout) + ' secs)...')
                timeout -= timeout
                # time.sleep(timeout)

        if timeout <= 0:
            raise Exception('Could not connect to AltUnrealServer on: '+ TCP_IP +':'+ str(self.TCP_PORT))

    def stop(self):
        if self.connect:
            CloseConnection(self.socket,self.request_separator,self.request_end).execute()
            self.connect = False 

    def find_object(self,value):
        return FindObject(self.socket,self.request_separator,self.request_end,value).execute()

    def find_object_and_tap(self,value):
        return FindObjectAndTap(self.socket,self.request_separator,self.request_end,value).execute()
    
    def find_object_and_click(self,value):
        return FindObjectAndClick(self.socket,self.request_separator,self.request_end,value).execute()
    
    def find_object_and_get_text(self,value):
        return FindObjectAndGetText(self.socket,self.request_separator,self.request_end,value).execute()
    
    def find_object_and_set_text(self,value,text):
        return FindObjectAndSetText(self.socket,self.request_separator,self.request_end,value,text).execute()

    def object_exist(self,value):
        return ObjectExist(self.socket,self.request_separator,self.request_end,value).execute()
    
    def object_exist_only_tap(self,value):
        return ObjectExistOnlyTap(self.socket,self.request_separator,self.request_end,value).execute()

    def get_screen(self):
        return GetScreen(self.socket,self.request_separator,self.request_end).execute()

    def find_child(self,value):
        return FindChild(self.socket,self.request_separator,self.request_end,value).execute()
    
    def find_child_id(self,value):
        return FindChildID(self.socket,self.request_separator,self.request_end,value).execute()

    def debug_mode(self,file_path = None, is_async=False):
        if self.debug_handler:
            try:
                self.debug_handler.stop()
            except:pass
            self.debug_handler = None
        
        self.debug_handler = DebugMode(self.socket,self.request_separator,self.request_end,file_path)
        if is_async:
            return self.debug_handler.async_record()
        else:
            return self.debug_handler.sync_record()
    
    def debug_mode_pause(self):
        if self.debug_handler:
            return self.debug_handler.pause()

    def debug_mode_resume(self):
        if self.debug_handler:
            return self.debug_handler.resume()
    
    def debug_mode_stop(self):
        if self.debug_handler:
            ret = self.debug_handler.stop()
        self.debug_handler = None
        return ret
    
    def is_debug_mode_record(self):
        if self.debug_handler:
            return self.debug_handler.is_record()

    def find_text(self, keyword=""):
        return FindText(self.socket,self.request_separator,self.request_end,keyword).execute()
    
    def find_text_mouse_tap(self, keyword,rx=0,ry=0,num=0):
        trt=FindText(self.socket,self.request_separator,self.request_end,keyword).execute()
        if trt != []:
            data = trt[num]  # 直接赋值，不用 json.loads()
            if self.platform == "PC":
                ClickScreen(data["x"] + rx, data["y"] + ry)
            else:
                self.clickScreen(data["x"] + rx, data["y"] + ry)
            return True
        return False

    def mouse_screen(self, xordic):
        MouseScreen(xordic["x"],xordic["y"])
        return True
    def custom_interface(self, command, *args):
        return CustomInterface(self.socket, self.request_separator, self.request_end, command, *args).execute()

    """获取插件版本"""
    def get_plugin_version(self):
        return getPluginVersion(self.socket, self.request_separator, self.request_end).execute()
    """获取引擎版本"""
    def get_engine_version(self):
        return GetEngineVersion(self.socket, self.request_separator, self.request_end).execute()
    """获取游戏版本"""
    def get_game_version(self):
        return GetGameVersion(self.socket, self.request_separator, self.request_end).execute()
    """获取游戏版本"""
    def get_game_name(self):
        return GetAppName(self.socket, self.request_separator, self.request_end).execute()
    """获取添加的所有api接口名"""
    def get_all_api(self):
        return CustomInterface(self.socket, self.request_separator, self.request_end, "help").execute()

    def GM(self, Command:str):
        """Command: GM 指令 """
        if "&" in Command:
            for Commandi in Command.split("&"):
                if Commandi ==" ":continue
                CustomInterface(self.socket, self.request_separator, self.request_end, "consoleCommand", Commandi).execute()
                time.sleep(0.5)
            return "success"
        else:
            return CustomInterface(self.socket, self.request_separator, self.request_end, "consoleCommand", Command).execute()
    
    def tapScreen(self, xordic,y = 0,operate = "down"):
        """ x,y
        operate: 操作["down","up"] 需要配合使用 按下 / 释放
        """
        if isinstance(xordic,dict):
            ret = CustomInterface(self.socket, self.request_separator, self.request_end, "tapScreen", xordic['x'],xordic['y'],operate).execute()
        else:
            ret = CustomInterface(self.socket, self.request_separator, self.request_end, "tapScreen", xordic,y,operate).execute()
        return ret
    
    def clickScreen(self, xordic,y=0):
        """ x,y
        operate: 
        """
        if isinstance(xordic,dict):
            ret = CustomInterface(self.socket, self.request_separator, self.request_end, "clickScreen", xordic['x'],xordic['y']).execute()
        else:
            ret = CustomInterface(self.socket, self.request_separator, self.request_end, "clickScreen", xordic,y).execute()
        return ret
    
    def getLocation(self):
        """ 
        operate: 获取玩家位置
        """
        ret=CustomInterface(self.socket, self.request_separator, self.request_end, "getLocation").execute()
        return json.loads(ret)
    
    def setLocation(self, xordic,y=0,z=0):
        """ x,y,z
        operate: 设置角色位置
        """
        if isinstance(xordic,dict):
            ret = CustomInterface(self.socket, self.request_separator, self.request_end, "setLocation", xordic['x'],xordic['y'],xordic['z']).execute()
        else:
            ret = CustomInterface(self.socket, self.request_separator, self.request_end, "setLocation", xordic,y,z).execute()
        return ret
    def getPRotation(self):
        """ 
        operate: 获取玩家旋转
        """

        ret = CustomInterface(self.socket, self.request_separator, self.request_end, "getPRotation").execute()
        return json.loads(ret)
    
    def setPRotation(self, xordic,y=0,r=0):
        """ Pitch,Yaw,Roll
        operate: 设置玩家旋转
        """
        if isinstance(xordic,dict):
            ret = CustomInterface(self.socket, self.request_separator, self.request_end, "setPRotation", xordic['p'],xordic['y'],xordic['r']).execute()
        else:
            ret = CustomInterface(self.socket, self.request_separator, self.request_end, "setPRotation", xordic,y,r).execute()
        return ret
    
    def getCRotation(self):
        """ 
        operate: 获取摄像机旋转角度
        """
        ret = CustomInterface(self.socket, self.request_separator, self.request_end, "getCRotation").execute()
        return json.loads(ret)
    
    def setCRotation(self, pordic,y=0,r=0):
        """ Pitch,Yaw,Roll
        operate: 设置摄像机旋转角度
        """
        if isinstance(pordic,dict):
            ret = CustomInterface(self.socket, self.request_separator, self.request_end, "setCRotation", pordic['p'],pordic['y'],pordic['r']).execute()
        else:
            ret = CustomInterface(self.socket, self.request_separator, self.request_end, "setCRotation", pordic,y,r).execute()
        return ret
    def getIndicatorLoc(self):
        """ 
        operate: 获取指引点坐标
        """
        ret = CustomInterface(self.socket, self.request_separator, self.request_end, "getIndicatorLoc").execute()
        return json.loads(ret)
    def getProjectileLoc(self):
        """ 
        operate: 获取电池掉落点坐标(是一个list 有多个电池)
        """
        ret = CustomInterface(self.socket, self.request_separator, self.request_end, "getProjectileLoc").execute()
        return json.loads(ret)
    
    def getTaskIndicatorLoc(self):
        """ 
        operate: 获取任务指引点坐标
        """
        ret = CustomInterface(self.socket, self.request_separator, self.request_end, "getTaskIndicatorLoc").execute()
        return json.loads(ret)
    
    def getMechanismLoc(self):
        """ 
        operate: 获取机关坐标
        """
        ret = CustomInterface(self.socket, self.request_separator, self.request_end, "getMechanismLoc").execute()
        return json.loads(ret)
    
    def findTextAndClick(self,keyword,which_num=0):
        """ 
        operate: 查找文本并点击
        keyword: 文本内容
        which_num: 点击第几个匹配项
        """
        ret = CustomInterface(self.socket, self.request_separator, self.request_end, "findTextAndClickWhich",keyword,which_num).execute()
        return json.loads(ret)
    
    def setAimRotation(self, xordic,y=0,z=0):
        """ 
        operate: 设置摄像机瞄准方向
        """
        if isinstance(xordic,dict):
            ret = CustomInterface(self.socket, self.request_separator, self.request_end, "setAimRotation", xordic['x'],xordic['y'],xordic['z']).execute()
        else:
            ret=  CustomInterface(self.socket, self.request_separator, self.request_end, "setAimRotation", xordic,y,z).execute()
        return  ret

    def unlockMiniGames(self):
        """ 
        operate: 解锁小游戏
        """
        return CustomInterface(self.socket, self.request_separator, self.request_end, "unlockMiniGames" ).execute()
    
    
    def findMonsterAndAim(self):
        """ 
        operate: 查找附近的怪物并瞄准它
        """
        return CustomInterface(self.socket, self.request_separator, self.request_end, "findMonsterAndAim" ).execute()
    
    def aimMonster(self,isAim):
        """ 
        operate: 瞄准怪物
        """
        return CustomInterface(self.socket, self.request_separator, self.request_end, "aimMonster",isAim).execute()
    
    #封装好的操作
    def behavior(self,keys,dimension=1):#dimension 次数 或者时间
        if keys=="子弹跳" or keys == "螺旋跳":
            self.inputAction("BulletJump")
        elif keys=="跳":
            self.inputAction("Jump")
        elif "连续前跳" in keys: #连续跳 需要dimension 跳的次数
            self.inputKeys("W","press")
            for _ in range(dimension):
                self.inputAction("Jump")
                time.sleep(0.5)
            self.inputKeys("W","release")
        elif "开枪" in keys:
            self.inputAction("Fire","press")
            time.sleep(dimension/2)
            self.inputAction("Fire","release")
            return 
        elif "挥刀" in keys:
            for _ in range(dimension):
                self.inputAction("Attack")
                time.sleep(0.5)
        elif "重击" in keys:
            self.inputAction("Attack","press")
            time.sleep(1.8)
            self.inputAction("Attack","release")
        elif "换子弹" in keys:
            self.inputAction("ChargeBullet")
            return
        elif "E技能" in keys:
            for _ in range(dimension):
                self.inputAction("Skill1")
                time.sleep(0.45)
        elif "Q技能" in keys:
            self.inputAction("Skill2")
        elif "宠物技能" in keys:
            self.inputKeys("Skill3")
        elif "下蹲" in keys:
            self.inputAction("SwitchCrouch")
        elif "打开地图" in keys:
            self.inputAction("OpenMap")
        elif "震地" in keys:
            self.inputAction("Jump")
            time.sleep(0.5)
            self.inputAction("Jump")
            time.sleep(0.5)
            self.inputAction("Attack")
        time.sleep(0.5)
        
    
    
    def inputAction(self,key,operate="click"):
        """
        key: "Attack","Jump","BulletJump","Skill1","Skill2","Skill3","Fire","ChargeBullet","SwitchCrouch","OpenMap"
        """
        return CustomInterface(self.socket, self.request_separator, self.request_end, "inputAction",key,operate).execute()

    def inputKeys(self,keys:str,operate="click",isplay="0"):
        """ 
        keys: 键入键盘(多个键使用, 分隔)
        operate: press/release/click (按/释放/点击)
        """
        if len(keys)==1:
            keys=keys.upper()
        if keys.lower()=="esc":
            keys="Escape"
        return CustomInterface(self.socket, self.request_separator, self.request_end, "inputKey" ,keys,operate,isplay).execute()
    
    def inputAxis(self,key,distance=10):
        """ 
        key: MouseX/MouseY
        operate: 水平或者上下移动鼠标
        """
        return CustomInterface(self.socket, self.request_separator, self.request_end, "inputAxis",key,distance ).execute()
    
    def switchWays(self):
        """ 
        directions: 切换路径寻找方式(默认是新的方式)
                    新的方式 自动匹配层级, 减少路径长度
                    旧的方式 完整的路径 (重复路径较多)
        """
        return CustomInterface(self.socket, self.request_separator, self.request_end, "switchWays" ).execute()
    
    def findMonsterLocation(self):
        """ 
        查找距离最近的怪物 获取它的坐标
        """
        ret =CustomInterface(self.socket, self.request_separator, self.request_end, "findMonsterLocation" ).execute()
        if ret=="error:no monsters" :return {}
        return json.loads(ret)
    
    def setMoveSpeed(self,times):
        """ 
        设置移动速度倍数 (相对于初始值)
        times:倍数
        """
        ret =CustomInterface(self.socket, self.request_separator, self.request_end, "setMoveSpeed",times).execute()
        return ret
    
    def runToLocation(self,xordict,y=0,z=0):
        """ 
        寻路, 走到指定坐标处
        """
        if isinstance(xordict,dict):
            ret = CustomInterface(self.socket, self.request_separator, self.request_end, "moveTo",xordict['x'],xordict['y'],xordict['z']).execute()
        else:
            ret = CustomInterface(self.socket, self.request_separator, self.request_end, "moveTo",xordict,y,z).execute()
        return ret
    
    def cameraFollow(self,isFollow):
        """ 
        镜头自动跟随
        """
        ret =CustomInterface(self.socket, self.request_separator, self.request_end, "cameraFollow",isFollow ).execute()
        return ret
    
    def isRun(self):
        """ 
        判断是否正在寻路
        """
        ret =CustomInterface(self.socket, self.request_separator, self.request_end, "isMove" ).execute()
        return ret
    
    def memReport(self):
        """ 
        截取内存报告Full
        返回memReport文件的绝对路径
        """
        ret =CustomInterface(self.socket, self.request_separator, self.request_end, "memReport").execute()
        return ret
    
    def getMapName(self):
        """ 
        获取地图名称
        """
        ret =CustomInterface(self.socket, self.request_separator, self.request_end, "getMapName").execute()
        return ret
    def setUseAccelerationForPaths(self,buse=1):
        """ 
        设置角色使用路径加速
        """
        ret =CustomInterface(self.socket, self.request_separator, self.request_end, "setUseAccelerationForPaths",buse).execute()
        return ret
    
    def captureStat(self,state,Pitem=[]):
        """ 
         采集stat性能数据
         1是开始
         0是结束
         返回 文件路径
        """
        if Pitem!=[]:
            ret =CustomInterface(self.socket, self.request_separator, self.request_end, "captureStat",state,*Pitem).execute()
        else:
            ret =CustomInterface(self.socket, self.request_separator, self.request_end, "captureStat",state).execute()
        return ret
    def scenePerfCheck(self,state,dist=600):
        """ 
         采集场景性能数据
         1是开始
         2是查询是否结束 如果结束了返回 文件路径
         -1 强制终止任务
        """
        ret =CustomInterface(self.socket, self.request_separator, self.request_end, "scenePerfCheck",state,dist).execute()
        return ret
    def getMechanismMaps(self,mapname=""):
        """ 
         获取机关maps数据
        """
        if mapname=="":
            ret =CustomInterface(self.socket, self.request_separator, self.request_end, "getMechanismMaps").execute()
        else:
            ret =CustomInterface(self.socket, self.request_separator, self.request_end, "getMechanismMaps",mapname).execute()
        return json.loads(ret)
    
    # 时间范围内持续查找控件并返回控件
    def find_object_until(self, value, wait=10, image_url=None):
        self.NeedPause()
        for i in range(0, wait):
            if ObjectExist(self.socket,self.request_separator,self.request_end,value).execute():
                return FindObject(self.socket,self.request_separator,self.request_end,value,image_url).execute()
            else:
                time.sleep(1)
        return FindObject(self.socket,self.request_separator,self.request_end,value,image_url).execute()
    
    #其他接口
    """演示新增一个接口
    CustomAPIDemo为接口名称
    args 为参数
    """
    def CustomAPIDemo(self, *args):
        return CustomInterface(self.socket, self.request_separator, self.request_end, "CustomAPIDemo", *args).execute()

