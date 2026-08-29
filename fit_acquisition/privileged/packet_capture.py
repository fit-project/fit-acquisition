from __future__ import annotations

import signal
import sys
import threading
from collections.abc import Callable

import scapy.all as scapy


def capture_to_stdout(ready: Callable[[], None]) -> None:
    stopped = threading.Event()
    signal.signal(signal.SIGTERM, lambda *_: stopped.set())
    sniffer = scapy.AsyncSniffer()
    sniffer.start()
    ready()
    stopped.wait()
    sniffer.stop()
    scapy.wrpcap(sys.stdout.buffer, sniffer.results)
