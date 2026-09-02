from __future__ import annotations

import ipaddress
import json
import os
import re
import sys
import tempfile
from pathlib import Path
from typing import Any, ClassVar, TextIO

import scapy.all as scapy

from .traceroute import run_traceroute

MAX_MESSAGE_SIZE = 1024 * 1024
_DESTINATION = re.compile(r"^[A-Za-z0-9.:-]{1,253}$")


class BrokerError(RuntimeError):
    def __init__(self, code: str, details: str):
        super().__init__(details)
        self.code = code
        self.details = details


class PrivilegedBroker:
    OPERATIONS: ClassVar[frozenset[str]] = frozenset(
        {
            "start_packet_capture",
            "stop_packet_capture",
            "traceroute",
            "shutdown",
        }
    )

    def __init__(self, acquisition_directory: str, stdin: TextIO, stdout: TextIO):
        self.base = Path(acquisition_directory).resolve()
        if not self.base.is_dir():
            raise BrokerError(
                "invalid_directory", "Acquisition directory does not exist"
            )
        self.stdin = stdin
        self.stdout = stdout
        self.sniffer = None
        self.capture_output: Path | None = None

    def _send(self, request_id: str | None, status: str, **payload: Any) -> None:
        message = {"request_id": request_id, "status": status, **payload}
        encoded = json.dumps(message, separators=(",", ":"))
        if len(encoded.encode("utf-8")) + 1 > MAX_MESSAGE_SIZE:
            raise BrokerError("message_too_large", "IPC response is too large")
        self.stdout.write(encoded + "\n")
        self.stdout.flush()

    def _output_path(self, value: Any) -> Path:
        if not isinstance(value, str) or not value:
            raise BrokerError("invalid_arguments", "Invalid output path")
        path = Path(value).resolve()
        if path.parent != self.base:
            raise BrokerError(
                "invalid_path", "Output path is outside acquisition directory"
            )
        return path

    def _write_pcap(self, path: Path, packets: Any) -> None:
        temporary_name = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w+b", prefix=".fit-pcap-", dir=self.base, delete=False
            ) as temporary:
                temporary_name = temporary.name
                scapy_output = os.fdopen(os.dup(temporary.fileno()), "wb")
                try:
                    scapy.wrpcap(scapy_output, packets)
                finally:
                    if not scapy_output.closed:
                        scapy_output.close()
                temporary.flush()
                os.fsync(temporary.fileno())
                os.fchmod(temporary.fileno(), 0o600)
                sudo_uid = os.environ.get("SUDO_UID")
                sudo_gid = os.environ.get("SUDO_GID")
                if sudo_uid and sudo_gid:
                    os.fchown(temporary.fileno(), int(sudo_uid), int(sudo_gid))
            os.replace(temporary_name, path)
            temporary_name = None
        finally:
            if temporary_name is not None:
                try:
                    os.unlink(temporary_name)
                except FileNotFoundError:
                    pass

    def _validate_request(self, message: Any) -> tuple[str, str, dict[str, Any]]:
        if not isinstance(message, dict):
            raise BrokerError("invalid_request", "Request must be an object")
        request_id = message.get("request_id")
        operation = message.get("operation")
        arguments = message.get("arguments")
        if not isinstance(request_id, str) or not request_id or len(request_id) > 128:
            raise BrokerError("invalid_request", "Invalid request ID")
        if operation not in self.OPERATIONS:
            raise BrokerError("invalid_operation", "Operation is not allowed")
        if not isinstance(arguments, dict):
            raise BrokerError("invalid_arguments", "Arguments must be an object")
        expected_arguments = {
            "start_packet_capture": {"output_path"},
            "stop_packet_capture": {"output_path"},
            "traceroute": {"destination"},
            "shutdown": set(),
        }
        if set(arguments) != expected_arguments[operation]:
            raise BrokerError("invalid_arguments", "Unexpected operation arguments")
        return request_id, operation, arguments

    @staticmethod
    def _valid_destination(destination: Any) -> bool:
        if not isinstance(destination, str) or not _DESTINATION.fullmatch(destination):
            return False
        try:
            ipaddress.ip_address(destination)
            return True
        except ValueError:
            labels = destination.rstrip(".").split(".")
            return all(
                label
                and len(label) <= 63
                and not label.startswith("-")
                and not label.endswith("-")
                for label in labels
            )

    def _handle(
        self, request_id: str, operation: str, arguments: dict[str, Any]
    ) -> bool:
        if operation == "start_packet_capture":
            if self.sniffer is not None:
                raise BrokerError("capture_active", "Packet capture is already active")
            path = self._output_path(arguments.get("output_path"))
            if path.exists() and not path.is_file():
                raise BrokerError("invalid_path", "Output path is not a file")
            self.sniffer = scapy.AsyncSniffer()
            try:
                self.sniffer.start()
            except Exception:
                self.sniffer = None
                raise
            self.capture_output = path
            self._send(request_id, "ready")
            return True
        if operation == "stop_packet_capture":
            if self.sniffer is None:
                raise BrokerError("capture_not_active", "Packet capture is not active")
            path = self._output_path(arguments.get("output_path"))
            if path != self.capture_output:
                raise BrokerError(
                    "invalid_path", "Output path differs from active capture"
                )
            sniffer = self.sniffer
            self.sniffer = None
            self.capture_output = None
            sniffer.stop()
            self._write_pcap(path, sniffer.results)
            self._send(request_id, "completed", result={"output_path": str(path)})
            return True
        if operation == "traceroute":
            destination = arguments.get("destination")
            if not self._valid_destination(destination):
                raise BrokerError(
                    "invalid_destination", "Invalid traceroute destination"
                )
            rows = run_traceroute(destination, lambda: self._send(request_id, "ready"))
            self._send(request_id, "completed", result=rows)
            return True
        if operation == "shutdown":
            if self.sniffer is not None:
                self.sniffer.stop()
                self.sniffer = None
                self.capture_output = None
            self._send(request_id, "completed", result={})
            return False
        raise BrokerError("invalid_operation", "Operation is not allowed")

    def run(self) -> int:
        self._send(None, "session_ready")
        for line in self.stdin:
            if len(line.encode("utf-8")) > MAX_MESSAGE_SIZE:
                self._send(
                    None,
                    "error",
                    error={
                        "code": "message_too_large",
                        "details": "IPC request is too large",
                    },
                )
                continue
            request_id = None
            try:
                message = json.loads(line)
                if isinstance(message, dict) and isinstance(
                    message.get("request_id"), str
                ):
                    request_id = message["request_id"]
                request_id, operation, arguments = self._validate_request(message)
                if not self._handle(request_id, operation, arguments):
                    return 0
            except (json.JSONDecodeError, UnicodeError):
                self._send(
                    request_id,
                    "error",
                    error={"code": "invalid_json", "details": "Malformed JSON request"},
                )
            except BrokerError as exc:
                self._send(
                    request_id,
                    "error",
                    error={"code": exc.code, "details": exc.details},
                )
            except Exception as exc:  # noqa: BLE001 - report operation failures over IPC
                self._send(
                    request_id,
                    "error",
                    error={"code": "operation_failed", "details": str(exc)},
                )
        if self.sniffer is not None:
            self.sniffer.stop()
            self.sniffer = None
            self.capture_output = None
        return 0


def run_broker(acquisition_directory: str) -> int:
    return PrivilegedBroker(acquisition_directory, sys.stdin, sys.stdout).run()
