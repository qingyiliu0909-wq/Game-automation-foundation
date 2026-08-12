import threading
import time
from pymobiledevice3.services.remote_server import MessageAux
from pymobiledevice3.services.dvt.instruments.device_info import DeviceInfo




class NetworkCollector:
    IDENTIFIER = 'com.apple.xcode.debug-gauge-data-providers.NetworkStatistics'

    def __init__(self, dvt, pid: str):
        self.dvt = dvt
        self.pid = pid
        self.channel = dvt.make_channel(self.IDENTIFIER)
        self.running = False
        self.thread = None
        self._queue = []
        self.lock = threading.Lock()



    def __enter__(self):
        # 启动采样器，参数要用 MessageAux 串联
        args = MessageAux().append_obj({self.pid})
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
        args = MessageAux().append_obj({self.pid})
        self.channel.send_message("stopSamplingForPIDs:", args)

    def _poll_data(self):
        while self.running:
            try:
                attr = {}
                args = MessageAux().append_obj(attr).append_obj({self.pid})
                self.channel.send_message("sampleAttributes:forPIDs:", args)
                ret = self.channel.receive_plist()
                if ret is None:
                    time.sleep(1)
                    continue
                elif not isinstance(ret,dict):
                    continue
                # print(ret)

                raw = ret.get(int(self.pid), {})

                parsed = self._parse_network_data(raw)
                with self.lock:
                    self._queue.append(parsed)
            except Exception as e:
                print("NetworkCollector error:", e)
            time.sleep(1)

    def _parse_network_data(self, data: dict):
        if not data:
            return {}
        def to_kb(value):
            """将字节（bytes）转换为千字节（KB），如果值存在并且为正"""
            return round(value / 1024, 2) if value and value > 0 else 0
        return {
            "Transmitted Bytes (KB)": to_kb(data.get("net.tx.bytes", 0)),
            "Received Bytes (KB)": to_kb(data.get("net.rx.bytes", 0)),
            "Total Network Bytes (KB)": to_kb(data.get("net.bytes", 0)),
            "Transmitted Packets": data.get("net.tx.packets", 0),
            "Received Packets": data.get("net.rx.packets", 0),
            "Total Network Packets": data.get("net.packets", 0),
            "Transmitted Bytes Delta (KB)": to_kb(data.get("net.tx.bytes.delta", 0)),
            "Received Bytes Delta (KB)": to_kb(data.get("net.rx.bytes.delta", 0)),
            "Transmitted Packets Delta": data.get("net.tx.packets.delta", 0),
            "Received Packets Delta": data.get("net.rx.packets.delta", 0),
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
