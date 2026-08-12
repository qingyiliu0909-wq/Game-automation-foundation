import psutil,socket,time,os,shutil,traceback
from loguru import  logger

def get_free_port():  
    sock = socket.socket()
    sock.bind(('', 0))
    sockname = sock.getsockname()
    sock.close()
    return sockname[1]

def get_pid(name):
    ppid=0
    for pid in psutil.process_iter():
        try:
            if(pid.name() == name):
                if name=="EM.exe":
                    if pid.parent()!=None and pid.parent().name()=="EM.exe":
                        ppid=pid.pid
                elif pid.pid>=ppid:
                    ppid=pid.pid
        except psutil.NoSuchProcess:
            logger.error(traceback.format_exc())
    return ppid

def del_file(file_dir,filter="",day=3):
    """清理三天前的文件"""
    if not os.path.exists(file_dir):return
    t=time.time()-86400*day
    try:
        for itme in os.listdir(file_dir):
            filepath=os.path.join(file_dir,itme)
            filetime= os.path.getmtime(filepath)
            if filetime<=t and filter in itme:
                #删除三天前的文件
                logger.info("removedirs",filepath)
                if os.path.isfile(filepath):
                    os.remove(filepath)
                else:
                    shutil.rmtree(filepath)
    except:
        logger.warning(traceback.format_exc())