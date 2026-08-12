import threading
import time
from pymobiledevice3.services.remote_server import MessageAux


class EnergyCollector:
    IDENTIFIER = 'com.apple.xcode.debug-gauge-data-providers.Energy'

    def __init__(self, dvt, pid: str):
        self.dvt = dvt
        self.pid = pid
        self.channel = dvt.make_channel(self.IDENTIFIER)
        self.running = False

        self.thread = None
        self._queue = []
        self.lock = threading.Lock()


    def __enter__(self):
        print(self.pid)
        args = MessageAux().append_obj({int(self.pid)})
        self.channel.send_message("startSamplingForPIDs:", args)
        self.running = True
        self.thread = threading.Thread(target=self._poll_data, daemon=True)
        self.thread.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.running = False
        if self.thread:
            self.thread.join()

        # 停止采样，参数格式同上
        args = MessageAux().append_obj({int(self.pid)})
        self.channel.send_message("stopSamplingForPIDs:", args)

    def _poll_data(self):
        while self.running:
            try:
                attr = {}
                args = MessageAux().append_obj(attr).append_obj({int(self.pid)})
                self.channel.send_message("sampleAttributes:forPIDs:", args)
                ret = self.channel.receive_plist()

                if ret is None:
                    print("sampleAttributes:forPIDs: 返回 None，跳过本次采样")
                    time.sleep(1)
                    continue
                elif not isinstance(ret,dict):
                    continue
                raw = ret.get(int(self.pid), {})

                parsed = self._parse_network_data(raw)
                with self.lock:
                    self._queue.append(parsed)
            except Exception as e:
                print("EnergyCollector error:", e)
            time.sleep(1)

    def _parse_network_data(self, data: dict):
        if not data:
            return {}
        def to_kj(value):
            """将焦耳（J）转换为千焦耳（kJ），如果值存在并且为正"""
            return round(value / 1000, 2) if value and value > 0 else 0

        return {
            "Total Energy (kJ)": to_kj(data.get("energy.cost", 0)),
            "CPU Energy (kJ)": to_kj(data.get("energy.cpu.cost", 0)),
            "GPU Energy (kJ)": to_kj(data.get("energy.gpu.cost", 0)),
            "Display Energy (kJ)": to_kj(data.get("energy.display.cost", 0)),
            "Network Energy (kJ)": to_kj(data.get("energy.networking.cost", 0)),
            "App Running State Energy (kJ)": to_kj(data.get("energy.appstate.cost", 0)),
            "Thermal State Energy (kJ)": to_kj(data.get("energy.thermalstate.cost", 0)),
        }

    def get_latest(self):
        with self.lock:
            return self._queue[-1] if self._queue else {}

    def get_all(self):
        with self.lock:
            return list(self._queue)

    def __iter__(self):
        while self.running:
            if self._queue:
                with self.lock:
                    yield self._queue.pop(0)
            else:
                time.sleep(0.5)

    # 方便外部主动停止
    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join()
        args = MessageAux().append_obj({self.pid})
        self.channel.send_message("stopSamplingForPIDs:", args)
