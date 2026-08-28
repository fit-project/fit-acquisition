"""Root-side CLI. It deliberately has no Qt imports."""

from __future__ import annotations

import argparse
import ipaddress
import json
import socket
import sys


def _destination(value: str) -> str:
    if not value or len(value) > 253 or any(c not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789.-:" for c in value):
        raise argparse.ArgumentTypeError("invalid destination")
    try:
        ipaddress.ip_address(value)
    except ValueError:
        if any(not label or len(label) > 63 for label in value.rstrip(".").split(".")):
            raise argparse.ArgumentTypeError("invalid destination")
        socket.getaddrinfo(value, None)
    return value


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="action", required=True)
    sub.add_parser("packet-capture")
    traceroute = sub.add_parser("traceroute")
    traceroute.add_argument("destination", type=_destination)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.action == "packet-capture":
        from .packet_capture import capture_to_stdout

        capture_to_stdout()
    elif args.action == "traceroute":
        from .traceroute import run_traceroute

        json.dump(run_traceroute(args.destination), sys.stdout)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
