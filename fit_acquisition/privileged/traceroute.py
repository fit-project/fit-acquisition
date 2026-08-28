from __future__ import annotations

import scapy.all as scapy


def run_traceroute(destination: str) -> list[dict[str, object]]:
    answered, _ = scapy.sr(
        scapy.IP(dst=destination, ttl=(1, 22), id=scapy.RandShort()) / scapy.TCP(flags=0x2),
        timeout=10,
        verbose=False,
    )
    return [
        {
            "ttl": int(sent.ttl),
            "ip": str(received.src),
            "tcp_response": isinstance(received.payload, scapy.TCP),
        }
        for sent, received in answered
    ]
