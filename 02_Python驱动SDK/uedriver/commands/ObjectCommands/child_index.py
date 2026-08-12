from uedriver.commands.base_command import BaseCommand
class ChildIndex(BaseCommand):
    def __init__(self, socket,request_separator,request_end,alt_object,value):
        super(ChildIndex, self).__init__(socket,request_separator,request_end)
        self.alt_object=alt_object
        self.value = value
    
    def execute(self):
        data=self.send_data(self.create_command('objectFind',self.alt_object,'index', self.value))
        return data