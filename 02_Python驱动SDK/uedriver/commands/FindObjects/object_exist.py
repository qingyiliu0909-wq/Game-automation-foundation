from uedriver.commands.command_returning_alt_elements import CommandReturningAltElements


class ObjectExist(CommandReturningAltElements):
    def __init__(self, socket,request_separator,request_end,value):
        super(ObjectExist, self).__init__(socket,request_separator,request_end)
        self.value=value

    def execute(self, false=False):
        data = self.send_data(self.create_command('objectExist', self.value))
        if data == '1' or data == 1:
            return True
        else:
            return false
        
class ObjectExistOnlyTap(CommandReturningAltElements):
    def __init__(self, socket,request_separator,request_end,value):
        super(ObjectExistOnlyTap, self).__init__(socket,request_separator,request_end)
        self.value=value

    def execute(self, false=False):
        data = self.send_data(self.create_command('objectExistOnlyTap', self.value))
        if data == '1' or data == 1:
            return True
        else:
            return false