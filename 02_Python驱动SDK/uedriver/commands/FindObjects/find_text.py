import json

from uedriver.commands.command_returning_alt_elements import \
    CommandReturningAltElements


class FindText(CommandReturningAltElements):
    def __init__(self, socket,request_separator,request_end,keyword):
        super(FindText, self).__init__(socket,request_separator,request_end)
        self.keyword = keyword
    
    def execute(self):
        data = self.send_data(self.create_command('findText',self.keyword))
        # Server may reply with plain-text errors (e.g. "error:notFound") instead of JSON.
        # Let BaseCommand handle them so callers get a clear NotFoundException, etc.
        if data and "error:" in data:
            self.handle_errors(data)
            return []
        if self.keyword:
            return [json.loads(i) for i in json.loads(data)]
        return json.loads(data)
