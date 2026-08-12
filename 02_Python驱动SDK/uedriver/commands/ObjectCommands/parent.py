from uedriver.commands.base_command import BaseCommand
class Parent(BaseCommand):
    def __init__(self, socket,request_separator,request_end,alt_object):
        super(Parent, self).__init__(socket,request_separator,request_end)
        self.alt_object=alt_object
    
    def execute(self):
        data=self.send_data(self.create_command('getParent',self.alt_object))
        return data
