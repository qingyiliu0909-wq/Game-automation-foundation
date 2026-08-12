from uedriver.commands.base_command import BaseCommand

class getPluginVersion(BaseCommand):
    def __init__(self, socket,request_separator,request_end):
        super(getPluginVersion,self).__init__(socket,request_separator,request_end)
    
    def execute(self):
        serverVersion=self.send_data(self.create_command('getPluginVersion'))
        return serverVersion
