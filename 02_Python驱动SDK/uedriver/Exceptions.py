class AltUnrealException(Exception):
    def __init__(self,message):
        super(AltUnrealException,self).__init__(message)
           
class NotFoundException(AltUnrealException):
    def __init__(self,message):
        super(NotFoundException,self).__init__(message)

class PropertyNotFoundException(AltUnrealException):
    def __init__(self,message):
        super(PropertyNotFoundException,self).__init__(message)

class MethodNotFoundException(AltUnrealException):
    def __init__(self,message):
        super(MethodNotFoundException,self).__init__(message)

class ComponentNotFoundException(AltUnrealException):
    def __init__(self,message):
        super(ComponentNotFoundException,self).__init__(message)

class CouldNotPerformOperationException(AltUnrealException):
    def __init__(self,message):
        super(CouldNotPerformOperationException,self).__init__(message)

class IncorrectNumberOfParametersException(AltUnrealException):
    def __init__(self,message):
        super(IncorrectNumberOfParametersException,self).__init__(message)

class CouldNotParseJsonStringException(AltUnrealException):
    def __init__(self,message):
        super(CouldNotParseJsonStringException,self).__init__(message)

class FailedToParseArgumentsException(AltUnrealException):
    def __init__(self,message):
        super(FailedToParseArgumentsException,self).__init__(message)

class ObjectWasNotFoundException(AltUnrealException):
    def __init__(self,message):
        super(ObjectWasNotFoundException,self).__init__(message)

class PropertyCannotBeSetException(AltUnrealException):
    def __init__(self,message):
        super(PropertyCannotBeSetException,self).__init__(message)

class NullReferenceException(AltUnrealException):
    def __init__(self,message):
        super(NullReferenceException,self).__init__(message)

class UnknownErrorException(AltUnrealException):
    def __init__(self,message):
        super(UnknownErrorException,self).__init__(message)

class FormatException(AltUnrealException):
    def __init__(self,message):
        super(FormatException,self).__init__(message)

class WaitTimeOutException(AltUnrealException):
    def __init__(self,message):
        super(WaitTimeOutException,self).__init__(message)
