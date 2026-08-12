from uedriver.commands.base_command import BaseCommand


class GetGameVersion(BaseCommand):
    def __init__(self, socket,request_separator,request_end):
        super(GetGameVersion, self).__init__(socket,request_separator,request_end)
    
    def execute(self):
        data=self.send_data(self.create_command('getAppName'))
        return data