import json
from uedriver.commands.ObjectCommands.get_text import GetText
from uedriver.commands.ObjectCommands.parent import Parent
from uedriver.commands.ObjectCommands.set_text import SetText
from uedriver.commands.ObjectCommands.tap import Tap
from uedriver.commands.custom_interface import CustomInterface
from uedriver.mouse_control import *

class AltElement(object):
    def __init__(self, alt_unreal_driver, json_data):
        self.alt_unreal_driver = alt_unreal_driver
        data = json.loads(json_data)
        try:
            self.name = str(data['name'])
        except:
            self.name = ""
        try:
            self.id = str(data['id'])
        except:
            self.id = ""
        self.x = ''#str(data['x'])
        self.y = ''#str(data['y'])
        try:
            if "x" in data:
                self.x = str(data['x'])
            if "y" in data:
                self.y = str(data['y'])
        except:
            pass

        self.text=""
        if "text" in data:
            self.text=str(data['text'])

    def toJSON(self):
        dict = {
            'name': self.name,
            'id' : self.id
        }
        return json.dumps(dict)

    def get_screen_position(self):
        return self.x, self.y
    
    def get_text(self):
        alt_object = self.toJSON()
        return GetText(self.alt_unreal_driver.socket,self.alt_unreal_driver.request_separator,self.alt_unreal_driver.request_end,alt_object).execute()
    
    def set_text(self, text):
        alt_object = self.toJSON()
        data = SetText(self.alt_unreal_driver.socket,self.alt_unreal_driver.request_separator,self.alt_unreal_driver.request_end,text,alt_object).execute()
        return AltElement(self.alt_unreal_driver, data)
    
    def tap(self):
        alt_object=self.toJSON()
        
        data= Tap(self.alt_unreal_driver.socket,self.alt_unreal_driver.request_separator,self.alt_unreal_driver.request_end,alt_object).execute()
        return AltElement(self.alt_unreal_driver, data)
    
    def mouse_tap(self,ClickType=1,duration=0):
        ClickScreen(self.x,self.y,ClickType,duration)
        return True
    
    def mouse_slide_position(self,x,y,duration=0):
        SlideScreen(self.x,self.y,x,y,duration)
        return True
    """滚动滚轮"""
    def mouse_scroll(self,x,y,delta=1):
        MoveAndScroll(self.x,self.y,x,y,delta)
        return True
    
    """滑动listview"""
    def setScrollOffset(self,delta=5):
        pathlist=[]
        if "/" in self.name:
            pathlist=self.name.split("/")
        else:
            pathlist=self.name.split("\\")
        if "SScrollBox" in pathlist[-1] or "SEMScrollBox" in pathlist[-1] or "ListViewT<ItemType>" in pathlist[-1] or "TileViewT<ItemType>" in  pathlist[-1]:
            alt_object=self.toJSON()
            return CustomInterface(self.alt_unreal_driver.socket,self.alt_unreal_driver.request_separator,self.alt_unreal_driver.request_end,"setScrollOffset",alt_object,delta).execute()
        else:
            print("路径不符合要求 需要使用 SScrollBox/ListViewT<ItemType> 结尾的组件")
            return "fail"

    def parent(self):
        alt_object=self.toJSON()
        data = Parent(self.alt_unreal_driver.socket,self.alt_unreal_driver.request_separator,self.alt_unreal_driver.request_end,alt_object).execute()
        return AltElement(self.alt_unreal_driver,data)
