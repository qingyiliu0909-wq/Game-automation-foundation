import logging
import tempfile
import threading
from functools import partial

from pymobiledevice3.lockdown import LockdownClient
from pymobiledevice3.tcp_forwarder import UsbmuxTcpForwarder

logger = logging.getLogger(__name__)


class TcpRelay:
    def __init__(self, service_provider: LockdownClient, device_port: int,
                 local_port: int, source: str = "127.0.0.1"):
        self.service_provider = service_provider
        self.device_port = device_port
        self.local_port = local_port
        self.source = source
        self.forwarder = None
        self._thread = None

    def start_relay(self, daemonize: bool = False):
        """启动 relay"""
        listening_event = threading.Event()
        self.forwarder = UsbmuxTcpForwarder(
            self.service_provider.udid,
            self.device_port,
            self.local_port,
            listening_event=listening_event
        )
        logger.info("Relay from %s:%d to device:%d", self.source, self.local_port, self.device_port)

        if daemonize:
            try:
                from daemonize import Daemonize
            except ImportError:
                raise NotImplementedError('daemonizing is only supported on unix platforms')

            with tempfile.NamedTemporaryFile('wt') as pid_file:
                daemon = Daemonize(
                    app=f'forwarder {self.local_port}->{self.device_port}',
                    pid=pid_file.name,
                    action=partial(self.forwarder.start, self.source),
                    verbose=True
                )
                daemon.start()
        else:
            # 开线程后台运行
            self._thread = threading.Thread(
                target=self.forwarder.start,
                args=(self.source,),
                daemon=True
            )
            self._thread.start()

    def stop_relay(self):
        """停止 relay"""
        if self.forwarder:
            self.forwarder.stop()
            logger.info("Relay stopped: %s:%d -> device:%d", self.source, self.local_port, self.device_port)
