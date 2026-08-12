from loguru import logger
import time
import socket as Socket
from uedriver.Exceptions import *
BUFFER_SIZE = 1024

class BaseCommand(object):
    def __init__(self, socket, request_separator=';', request_end='&'):
        self.request_separator = request_separator
        self.request_end = request_end
        self.socket:Socket.socket = socket
    '''接收数据'''
    def recvall(self):
        data = ''
        self.recvalling = True
        start = int(time.time())
        while True:
            part = self.socket.recv(BUFFER_SIZE)
            data += str(part.decode('utf-8', "ignore"))
            if len(part) == 0:
                end = int(time.time())
                if end - start >= 60:
                    raise Exception(f"socket disconnected: {data}")
            if "::altend" in data:
                #TODO 当本次信息读取结束后 判断一下缓冲区是否还有数据
                # data = self.socket.recv(BUFFER_SIZE)
                break
            if not self.recvalling:
                return ''
        try:
            data = data.split('altstart::')[1].split('::altend')[0]
            splitted_string = data.split('::altLog::')
            data = splitted_string[0]
        except:
            logger.error('Data received from socket does not have correct start and end control strings')
            return ''
        logger.info('<= ' + data)
        return data
    '''停止接收数据'''
    def stop_recvall(self):
        self.recvalling = False
    '''清理缓冲区数据'''
    def clear_recv(self):
        self.socket.setblocking(False)
        while True:
            try:
                data=self.socket.recvfrom(2048)
                if data!=None:
                    logger.info("缓存区的数据(已清理)",data)
            except Exception as e:
                #logger.info str(e)
                break
        self.socket.setblocking(True)

    def handle_errors(self, data):
        if ('error:' in data):
            if ('error:notFound' in data):
                raise NotFoundException(data)
            elif ('error:propertyNotFound' in data):
                raise PropertyNotFoundException(data)
            elif ('error:methodNotFound' in data):
                raise MethodNotFoundException(data)
            elif ('error:componentNotFound' in data):
                raise ComponentNotFoundException(data)
            elif ('error:couldNotPerformOperation' in data):
                raise CouldNotPerformOperationException(data)
            elif ('error:couldNotParseJsonString' in data):
                raise CouldNotParseJsonStringException(data)
            elif ('error:incorrectNumberOfParameters' in data):
                raise IncorrectNumberOfParametersException(data)
            elif ('error:failedToParseMethodArguments' in data):
                raise FailedToParseArgumentsException(data)
            elif ('error:objectNotFound' in data):
                raise ObjectWasNotFoundException(data)
            elif ('error:propertyCannotBeSet' in data):
                raise PropertyNotFoundException(data)
            elif ('error:nullReferenceException' in data):
                raise NullReferenceException(data)
            elif ('error:unknownError' in data):
                raise UnknownErrorException(data)
            elif ('error:formatException' in data):
                raise FormatException(data)
            else:
                raise Exception(data)
        else:
            return data
        
    def vector_to_json_string(self, x, y, z=None):
        if z is None:
            return '{"x":' + str(x) + ', "y":' + str(y) + '}'
        else:
            return '{"x":' + str(x) + ', "y":' + str(y) +', "z":' + str(z) + '}'

    def positions_to_json_string(self, positions):
        json_positions = [self.vector_to_json_string(p[0], p[1]) for p in positions]
        return self.request_separator.join(json_positions)
    
    def send_data(self, data):
        logger.info(f"=>{data}")
        self.socket.send(data.encode('utf-8'))
        # logger.info("send data finish")
        if ('closeConnection' in data):
            return ''
        elif ('stopDebugMode' in data):
            return ''
        elif ('pauseDebugMode' in data):
            return ''
        # elif ('resumeDebugMode' in data):
        #     return ''
        else:
            return self.recvall()

    def create_command(self, *arguments):
        command = ''
        for argument in arguments:
            argument=str(argument)
            command += str(argument)+self.request_separator
        command += self.request_end
        return command
