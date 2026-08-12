from pymobiledevice3.lockdown import LockdownClient
from pymobiledevice3.services.dvt.dvt_secure_socket_proxy import DvtSecureSocketProxyService
from pymobiledevice3.services.dvt.instruments.graphics import Graphics
import threading
from queue import Queue, Empty

class GPU:
    def __init__(self, service_provider: LockdownClient):
        self.service_provider = service_provider
        self.running = False
        self.latest_stats = None
        self._thread = None
        self._queue = Queue()

    def _worker(self):
        """内部线程函数，不断从graphics迭代器读取数据"""
        with DvtSecureSocketProxyService(lockdown=self.service_provider) as dvt:
            with Graphics(dvt) as graphics:
                for stats in graphics:
                    if not self.running:
                        break
                    self._queue.put(stats)
                    self.latest_stats = stats

    def start(self):
        if self.running:
            print("Already running")
            return
        self.running = True
        self._thread = threading.Thread(target=self._worker, daemon=True)
        self._thread.start()
        print("采集开始")

    def stop(self):
        if not self.running:
            print("Not running")
            return
        self.running = False
        self._thread.join()
        print("采集结束")

    def get_latest(self):
        """获取当前最新采集的数据"""
        return self.latest_stats

    def get_all(self, timeout=1):
        """尝试获取采集期间所有未处理的消息"""
        messages = []
        while True:
            try:
                msg = self._queue.get(timeout=timeout)
                messages.append(msg)
            except Empty:
                break
        return messages

