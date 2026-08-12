from uedriver.commands.base_command import BaseCommand


class GetAppName(BaseCommand):
    def __init__(self, socket,request_separator,request_end):
        super(GetAppName, self).__init__(socket,request_separator,request_end)
    
    def execute(self):
        data=self.send_data(self.create_command('getAppName'))
        return data