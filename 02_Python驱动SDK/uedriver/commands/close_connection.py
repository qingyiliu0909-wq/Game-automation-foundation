import time
from loguru import logger
from uedriver.commands.base_command import BaseCommand


class CloseConnection(BaseCommand):
    def __init__(self, socket,request_separator,request_end):
        super(CloseConnection, self).__init__(socket,request_separator,request_end)
    
    def execute(self):
        data = self.send_data(self.create_command('closeConnection'))
        logger.warning('Sent close connection command...')
        time.sleep(1)
        self.socket.close()
        self.connect = False
        logger.warning('Socket closed.')  
        