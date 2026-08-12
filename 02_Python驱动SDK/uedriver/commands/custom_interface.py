from uedriver.commands.base_command import BaseCommand


class CustomInterface(BaseCommand):
    def __init__(self, socket,request_separator,request_end,command,*args):
        super(CustomInterface, self).__init__(socket,request_separator,request_end)
        self.command = command
        self.args = args
    
    def execute(self):
        data=self.send_data(self.create_command(self.command, *self.args))
        return data
