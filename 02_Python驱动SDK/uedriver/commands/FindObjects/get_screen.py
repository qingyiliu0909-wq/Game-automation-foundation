import json

from uedriver.commands.command_returning_alt_elements import CommandReturningAltElements


class GetScreen(CommandReturningAltElements):
    def __init__(self, socket,request_separator,request_end):
        super(GetScreen, self).__init__(socket,request_separator,request_end)
    
    def execute(self):
        json_data = self.send_data(self.create_command('getScreen'))
        print(type(json_data))
        data = json.loads(json_data)
        return data['width'], data['height']