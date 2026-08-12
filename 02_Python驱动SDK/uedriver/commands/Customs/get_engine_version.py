from uedriver.commands.base_command import BaseCommand


class GetEngineVersion(BaseCommand):
    def __init__(self, socket,request_separator,request_end):
        super(GetEngineVersion, self).__init__(socket,request_separator,request_end)
    
    def execute(self):
        data=self.send_data(self.create_command('getEngineVersion'))
        return data
