import json
from loguru import logger
from uedriver.altElement import AltElement
from uedriver.commands.base_command import BaseCommand

BUFFER_SIZE = 1024
class CommandReturningAltElements(BaseCommand):
    def __init__(self, socket,request_separator,request_end):
        self.request_separator=request_separator
        self.request_end=request_end
        self.socket=socket

    def get_alt_element(self, data):
        # logger.info(data)
        if (data != '' and 'error:' not in data):
            return AltElement(self, data)
        self.handle_errors(data)
        return None
