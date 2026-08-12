import struct
import uuid
from statistics import mean
from datetime import datetime
from pymobiledevice3.services.remote_server import MessageAux

def kperf_data(messages):
    _list = []
    p_record = 0
    m_len = len(messages)
    if m_len % 64 != 0:
        return _list
    while p_record < m_len:
        _list.append(struct.unpack('<QLLQQQQLLQ', messages[p_record:p_record + 64]))
        p_record += 64
    return _list

class FPSCollector:
    IDENTIFIER = "com.apple.instruments.server.services.coreprofilesessiontap"
    DEVICEINFO_IDENTIFIER = "com.apple.instruments.server.services.deviceinfo"

    def __init__(self, dvt):
        self.dvt = dvt
        self.channel = dvt.make_channel(self.IDENTIFIER)
        self.mach_time_factor = 1.0

    def __enter__(self):
        # 通过设备信息服务获取 machTimeInfo
        device_info_channel = self.dvt.make_channel(self.DEVICEINFO_IDENTIFIER)
        device_info_channel.send_message('machTimeInfo')
        mach_time_info = device_info_channel.receive_plist()

        if mach_time_info is None or not isinstance(mach_time_info, (list, tuple)) or len(mach_time_info) < 3:
            raise RuntimeError("获取 machTimeInfo 失败或数据格式异常: " + str(mach_time_info))

        # mach_time_info一般结构是类似 [timebase numerator, timebase denominator, frequency]，具体请确认
        self.mach_time_factor = mach_time_info[1] / mach_time_info[2]

        config = {
            'rp': 10,
            'tc': [{
                'kdf2': [630784000, 833617920, 830472456],  # 这里是列表，非集合
                'tk': 3,
                'uuid': str(uuid.uuid4()).upper()
            }],
            'ur': 500
        }

        args = MessageAux().append_obj(config)
        self.channel.send_message('setConfig:', args)
        self.channel.send_message('start')
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.channel.send_message('stop')

    def __iter__(self):
        last_frame = None
        last_costs = [0, 0, 0]
        jank_count = 0
        big_jank_count = 0
        jank_time_count = 0
        frame_count = 0
        time_count = 0
        last_time = datetime.now().timestamp()
        MOVIE_FRAME_COST = 1 / 24
        NANO_SECOND = 1e9

        while True:
            data, aux = self.channel.receive_key_value()
            if not data:
                continue
            try:
                frame_data = kperf_data(data)  # 用你的二进制解析函数
            except Exception as e:
                print("❌ kperf_data 解析失败:", e)
                print("原始数据:", data[:100])
                continue

            for item in frame_data:
                # item 是 tuple，符合你 kperf_data 解包格式
                _time, code = item[0], item[7]

                if code != 830472984:
                    continue
                this_cost = (_time - last_frame) * self.mach_time_factor if last_frame else 0
                last_frame = _time

                if all(last_costs):
                    avg = mean(last_costs)
                    if this_cost > avg * 2 and this_cost > MOVIE_FRAME_COST * NANO_SECOND * 2:
                        jank_count += 1
                        jank_time_count += this_cost
                        if this_cost > avg * 3:
                            big_jank_count += 1

                last_costs = [last_costs[1], last_costs[2], this_cost]
                frame_count += 1
                time_count += this_cost

                if time_count > NANO_SECOND:
                    now = datetime.now().timestamp()
                    yield {
                        "elapsed_time": now - last_time,
                        "fps": frame_count / time_count * NANO_SECOND,
                        "jank_count": jank_count,
                        "big_jank_count": big_jank_count,
                        "stutter": jank_time_count / time_count if time_count else 0,
                        "count_time": now
                    }
                    frame_count = 0
                    time_count = 0
                    jank_count = 0
                    big_jank_count = 0
                    jank_time_count = 0
                    last_time = now