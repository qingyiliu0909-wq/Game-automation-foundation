import json

from uedriver.commands.command_returning_alt_elements import CommandReturningAltElements


class FindChild(CommandReturningAltElements):
    def __init__(self, socket,request_separator,request_end,value):
        super(FindChild, self).__init__(socket,request_separator,request_end)
        self.value=value
    
    def execute(self):
        data = self.send_data(self.create_command('findChild', self.value))
        # Server may reply with plain-text errors (e.g. "error:notFound") instead of JSON.
        # Let BaseCommand handle them so callers get a clear NotFoundException, etc.
        if data and "error:" in data:
            self.handle_errors(data)
            return []
        return [i['name'] for i in json.loads(data)]
    
class FindChildID(CommandReturningAltElements):
    def __init__(self, socket,request_separator,request_end,value):
        super(FindChild, self).__init__(socket,request_separator,request_end)
        self.value=value
    
    def execute(self):
        data = self.send_data(self.create_command('findChild', self.value))
        if data and "error:" in data:
            self.handle_errors(data)
            return []
        return [i['id'] for i in json.loads(data)]
