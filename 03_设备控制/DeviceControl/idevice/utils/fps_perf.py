import threading
from queue import Queue, Empty
from pymobiledevice3.lockdown import LockdownClient
from pymobiledevice3.services.dvt.dvt_secure_socket_proxy import DvtSecureSocketProxyService
from DeviceControl.idevice.utils.FPS import FPSCollector  # 你可以将上面 FPSCollector 保存为 fps_collector.py

class FPS:
    def __init__(self, service_provider: LockdownClient):
        self.service_provider = service_provider
        self.running = False
        self.latest_fps = None
        self._thread = None
        self._queue = Queue()

    def _worker(self):
        with DvtSecureSocketProxyService(lockdown=self.service_provider) as dvt:
            with FPSCollector(dvt) as collector:
                for stats in collector:

                    if not self.running:
                        break
                    self._queue.put(stats)
                    self.latest_fps = stats

    def start(self):
        if self.running:
            print("FPS 已经在运行")
            return
        self.running = True
        self._thread = threading.Thread(target=self._worker, daemon=True)
        self._thread.start()
        print("FPS 采集启动")

    def stop(self):
        if not self.running:
            print("FPS 未运行")
            return
        self.running = False
        self._thread.join()
        print("FPS 采集停止")

    def get_latest(self):
        return self.latest_fps

    def get_all(self, timeout=1):
        results = []
        while True:
            try:
                res = self._queue.get(timeout=timeout)
                results.append(res)
            except Empty:
                break
        return results
