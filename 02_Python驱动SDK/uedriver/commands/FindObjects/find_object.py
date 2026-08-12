import json
from uedriver.commands.command_returning_alt_elements import CommandReturningAltElements

class FindObject(CommandReturningAltElements):
    def __init__(self, socket,request_separator,request_end,value):
        super(FindObject, self).__init__(socket,request_separator,request_end)
        self.value=str(value)
        self.type="path" if isinstance(value,str) and (not value.isdigit()) else "id"
    
    def execute(self):
        data = self.send_data(self.create_command('findObject', self.value, self.type))
        return self.get_alt_element(data)
    
class FindObjectAndClick(CommandReturningAltElements):
    def __init__(self, socket,request_separator,request_end,value):
        super(FindObjectAndClick, self).__init__(socket,request_separator,request_end)
        self.value=value
    
    def execute(self):
        data = self.send_data(self.create_command('findObject', self.value , "path","click"))
        return self.get_alt_element(data)
    
class FindObjectAndGetText(CommandReturningAltElements):
    def __init__(self, socket,request_separator,request_end,value):
        super(FindObjectAndGetText, self).__init__(socket,request_separator,request_end)
        self.value=value

    def execute(self):
        data = self.send_data(self.create_command('findObject', self.value , "path","get_text"))
        data=self.get_alt_element(data)
        if data!=None:
            return data.text
        return ""
    
class FindObjectAndSetText(CommandReturningAltElements):
    def __init__(self, socket,request_separator,request_end,value,text):
        super(FindObjectAndSetText, self).__init__(socket,request_separator,request_end)
        self.value=value
        self.text=text

    def execute(self):
        data = self.send_data(self.create_command('findObject', self.value , "path","set_text",self.text))
        return self.get_alt_element(data)
    
class FindObjectAndTap(CommandReturningAltElements):
    def __init__(self, socket,request_separator,request_end,value):
        super(FindObjectAndTap, self).__init__(socket,request_separator,request_end)
        self.value=value
        self.type="path" if isinstance(value,str) and (not value.isdigit()) else "id"
    
    def execute(self):
        data = self.send_data(self.create_command('findObject', self.value,self.type,"tap"))
        # Server may reply with plain-text errors (e.g. "error:notFound") instead of JSON.
        # Let BaseCommand handle them so callers get a clear NotFoundException, etc.
        if data and "error:" in data:
            self.handle_errors(data)
            return None
        return json.loads(data)