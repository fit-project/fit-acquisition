from __future__ import annotations

from collections.abc import Callable

import scapy.all as scapy


def run_traceroute(
    destination: str, ready: Callable[[], None]
) -> list[dict[str, object]]:
    packets = (
        scapy.IP(dst=destination, ttl=(1, 22), id=scapy.RandShort())
        / scapy.TCP(flags=0x2)
    )
    socket = scapy.conf.L3socket()
    try:
        ready()
        answered, _ = scapy.sr(
            packets,
            timeout=10,
            verbose=False,
            opened_socket=socket,
        )
    finally:
        socket.close()
    return [
        {
            "ttl": int(sent.ttl),
            "ip": str(received.src),
            "tcp_response": isinstance(received.payload, scapy.TCP),
        }
        for sent, received in answered
    ]
