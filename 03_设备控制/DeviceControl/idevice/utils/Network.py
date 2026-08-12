import threading
from queue import Queue, Empty
from pymobiledevice3.lockdown import LockdownClient
from pymobiledevice3.services.dvt.dvt_secure_socket_proxy import DvtSecureSocketProxyService
from DeviceControl.idevice.utils.NetworkCollector import NetworkCollector

class NetworkSampler:
    def __init__(self, service_provider: LockdownClient, pid: str):
        self.service_provider = service_provider
        self.pid = pid
        self.running = False
        self.latest_data = None
        self._thread = None
        self._queue = Queue()

    def _worker(self):
        with DvtSecureSocketProxyService(lockdown=self.service_provider) as dvt:
            with NetworkCollector(dvt, self.pid) as collector:
                for data in collector:
                    if not self.running:
                        break
                    self._queue.put(data)
                    self.latest_data = data

    def start(self):
        if self.running:
            print("📡 NetworkSampler 已经运行")
            return
        self.running = True
        self._thread = threading.Thread(target=self._worker, daemon=True)
        self._thread.start()
        print("📡 网络采样启动")

    def stop(self):
        if not self.running:
            print("🛑 NetworkSampler 未运行")
            return
        self.running = False
        self._thread.join()
        print("🛑 网络采样停止")

    def get_latest(self):
        return self.latest_data

    def get_all(self, timeout=1):
        results = []
        while True:
            try:
                res = self._queue.get(timeout=timeout)
                results.append(res)
            except Empty:
                break
        return results
