from __future__ import annotations

import json
import logging
import os
import shutil
import signal
import subprocess
import sys
import threading
import time
import uuid
from collections import OrderedDict
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, ClassVar

from .runner import PrivilegedProcessError

SESSION_READY = "session_ready"
MAX_MESSAGE_SIZE = 1024 * 1024
DEFAULT_STARTUP_TIMEOUT = 60.0
DEFAULT_REQUEST_TIMEOUT = 30.0
TERMINATION_TIMEOUT = 5.0
MAX_EXPIRED_REQUESTS = 1024
logger = logging.getLogger(__name__)


@dataclass
class _PendingRequest:
    condition: threading.Condition = field(default_factory=threading.Condition)
    ready: bool = False
    response: dict[str, Any] | None = None
    error: PrivilegedProcessError | None = None


class PrivilegedSession:
    """One lazy Linux-only privileged broker for a single acquisition."""

    OPERATIONS: ClassVar[frozenset[str]] = frozenset(
        {
            "start_packet_capture",
            "stop_packet_capture",
            "traceroute",
            "shutdown",
        }
    )

    def __init__(self, acquisition_directory: str | None = None) -> None:
        self.acquisition_directory = acquisition_directory
        self._process: subprocess.Popen[bytes] | None = None
        self._state_condition = threading.Condition()
        self._write_lock = threading.Lock()
        self._start_lock = threading.Lock()
        self._pending_lock = threading.Lock()
        self._pending: dict[str, _PendingRequest] = {}
        self._expired: OrderedDict[str, None] = OrderedDict()
        self._session_ready = False
        self._closed = False
        self._failure: PrivilegedProcessError | None = None
        self._stderr = bytearray()

    @property
    def active(self) -> bool:
        with self._state_condition:
            return (
                self._process is not None
                and self._process.poll() is None
                and self._session_ready
                and not self._closed
            )

    @staticmethod
    def _environment() -> dict[str, str]:
        askpass = os.environ.get("FIT_LINUX_SUDO_ASKPASS")
        if not askpass or not Path(askpass).is_file():
            raise PrivilegedProcessError(
                "askpass_missing", "FIT_LINUX_SUDO_ASKPASS is not configured"
            )
        environment = os.environ.copy()
        environment["SUDO_ASKPASS"] = askpass
        return environment

    def _command(self) -> list[str]:
        if sys.platform != "linux":
            raise PrivilegedProcessError(
                "unsupported_platform", "Privileged sessions are Linux-only"
            )
        if not self.acquisition_directory:
            raise PrivilegedProcessError(
                "invalid_directory", "The acquisition directory is unavailable"
            )
        sudo = shutil.which("sudo")
        if sudo is None:
            raise PrivilegedProcessError("sudo_missing", "sudo is not available")
        return [
            sudo,
            "-A",
            sys.executable,
            "-m",
            "fit_acquisition.privileged.cli",
            "broker",
            str(Path(self.acquisition_directory).resolve()),
        ]

    def start(self, timeout: float = DEFAULT_STARTUP_TIMEOUT) -> None:
        with self._start_lock:
            if self.active:
                return
            with self._state_condition:
                if self._closed:
                    raise PrivilegedProcessError(
                        "session_closed", "The privileged session is closed"
                    )
                if self._failure is not None:
                    raise self._failure
                process = subprocess.Popen(
                    self._command(),
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    env=self._environment(),
                    shell=False,
                    start_new_session=True,
                )
                self._process = process

            stdout_reader = threading.Thread(
                target=self._read_stdout, args=(process,), daemon=True
            )
            stderr_reader = threading.Thread(
                target=self._read_stderr, args=(process,), daemon=True
            )
            stdout_reader.start()
            stderr_reader.start()
            threading.Thread(
                target=self._watch,
                args=(process, stdout_reader, stderr_reader),
                daemon=True,
            ).start()

            deadline = time.monotonic() + timeout
            with self._state_condition:
                while not self._session_ready and self._failure is None:
                    remaining = deadline - time.monotonic()
                    if remaining <= 0:
                        break
                    self._state_condition.wait(remaining)
                if self._session_ready:
                    return
                error = self._failure or PrivilegedProcessError(
                    "readiness_timeout", "Privileged session readiness timed out"
                )
            self._terminate(process)
            self._fail(error)
            raise error

    def request(
        self,
        operation: str,
        arguments: dict[str, Any] | None = None,
        *,
        timeout: float = DEFAULT_REQUEST_TIMEOUT,
        on_ready: Callable[[], None] | None = None,
        return_on_ready: bool = False,
    ) -> Any:
        if operation not in self.OPERATIONS or operation == "shutdown":
            raise PrivilegedProcessError(
                "invalid_operation", "Operation is not allowed"
            )
        self.start()
        request_id = uuid.uuid4().hex
        pending = _PendingRequest()
        with self._pending_lock:
            self._pending[request_id] = pending
        try:
            self._send(
                {
                    "request_id": request_id,
                    "operation": operation,
                    "arguments": arguments or {},
                }
            )
            deadline = time.monotonic() + timeout
            ready_reported = False
            with pending.condition:
                while pending.response is None and pending.error is None:
                    if pending.ready and not ready_reported:
                        ready_reported = True
                        if on_ready is not None:
                            on_ready()
                        if return_on_ready:
                            return None
                    remaining = deadline - time.monotonic()
                    if remaining <= 0:
                        error = PrivilegedProcessError(
                            "timeout", f"Privileged operation {operation} timed out"
                        )
                        with self._pending_lock:
                            self._pending.pop(request_id, None)
                            self._expired[request_id] = None
                            self._expired.move_to_end(request_id)
                            while len(self._expired) > MAX_EXPIRED_REQUESTS:
                                self._expired.popitem(last=False)
                        logger.warning(
                            "Privileged request timed out request_id=%s operation=%s",
                            request_id,
                            operation,
                        )
                        raise error
                    pending.condition.wait(remaining)
                if pending.ready and not ready_reported:
                    ready_reported = True
                    if on_ready is not None:
                        on_ready()
                    if return_on_ready:
                        return None
                if pending.error is not None:
                    raise pending.error
                assert pending.response is not None
                response = pending.response
            if response["status"] == "error":
                error = response.get("error", {})
                raise PrivilegedProcessError(
                    str(error.get("code", "operation_failed")),
                    str(error.get("details", "Privileged operation failed")),
                )
            result = response.get("result")
            if operation == "traceroute":
                self._validate_traceroute_result(result)
            return result
        finally:
            with self._pending_lock:
                self._pending.pop(request_id, None)

    def _send(self, message: dict[str, Any]) -> None:
        encoded = json.dumps(message, separators=(",", ":")).encode("utf-8") + b"\n"
        if len(encoded) > MAX_MESSAGE_SIZE:
            raise PrivilegedProcessError(
                "message_too_large", "IPC message is too large"
            )
        with self._write_lock:
            process = self._process
            if process is None or process.stdin is None or process.poll() is not None:
                raise PrivilegedProcessError(
                    "session_ended", "Privileged session ended"
                )
            try:
                process.stdin.write(encoded)
                process.stdin.flush()
            except (BrokenPipeError, OSError) as exc:
                raise PrivilegedProcessError("session_ended", str(exc)) from exc

    @staticmethod
    def _validate_traceroute_result(result: Any) -> None:
        if not isinstance(result, list):
            raise PrivilegedProcessError("invalid_output", "Invalid traceroute result")
        for row in result:
            if (
                not isinstance(row, dict)
                or not isinstance(row.get("ttl"), int)
                or isinstance(row.get("ttl"), bool)
                or not isinstance(row.get("ip"), str)
                or not isinstance(row.get("tcp_response"), bool)
            ):
                raise PrivilegedProcessError(
                    "invalid_output", "Invalid traceroute result"
                )

    def _read_stdout(self, process: subprocess.Popen[bytes]) -> None:
        assert process.stdout is not None
        while True:
            line = process.stdout.readline(MAX_MESSAGE_SIZE + 1)
            if not line:
                return
            if len(line) > MAX_MESSAGE_SIZE or not line.endswith(b"\n"):
                self._fail(
                    PrivilegedProcessError("protocol_error", "Invalid IPC frame")
                )
                return
            try:
                message = json.loads(line)
            except (UnicodeDecodeError, json.JSONDecodeError):
                self._fail(
                    PrivilegedProcessError("protocol_error", "Malformed IPC message")
                )
                return
            self._dispatch(message)

    def _dispatch(self, message: Any) -> None:
        if not isinstance(message, dict):
            self._fail(
                PrivilegedProcessError(
                    "protocol_error", "IPC message must be an object"
                )
            )
            return
        if message.get("status") == SESSION_READY and message.get("request_id") is None:
            with self._state_condition:
                if self._session_ready:
                    self._fail(
                        PrivilegedProcessError(
                            "protocol_error", "Duplicate SESSION_READY"
                        )
                    )
                    return
                self._session_ready = True
                self._state_condition.notify_all()
            return
        request_id = message.get("request_id")
        status = message.get("status")
        if not isinstance(request_id, str) or status not in {
            "ready",
            "completed",
            "error",
        }:
            self._fail(PrivilegedProcessError("protocol_error", "Invalid IPC response"))
            return
        with self._pending_lock:
            pending = self._pending.get(request_id)
            expired = request_id in self._expired
            if expired and status in {"completed", "error"}:
                self._expired.pop(request_id, None)
        if pending is None:
            if expired:
                logger.debug(
                    "Ignored late IPC response request_id=%s status=%s",
                    request_id,
                    status,
                )
                return
            self._fail(PrivilegedProcessError("protocol_error", "Unknown request ID"))
            return
        with pending.condition:
            if pending.response is not None or (status == "ready" and pending.ready):
                self._fail(
                    PrivilegedProcessError("protocol_error", "Duplicate response")
                )
                return
            if status == "ready":
                pending.ready = True
            else:
                pending.response = message
            pending.condition.notify_all()

    def _read_stderr(self, process: subprocess.Popen[bytes]) -> None:
        assert process.stderr is not None
        while chunk := process.stderr.read(64 * 1024):
            with self._state_condition:
                self._stderr.extend(chunk)

    def _watch(
        self,
        process: subprocess.Popen[bytes],
        stdout_reader: threading.Thread,
        stderr_reader: threading.Thread,
    ) -> None:
        process.wait()
        stdout_reader.join()
        stderr_reader.join()
        with self._state_condition:
            expected = self._closed
        if not expected:
            details = bytes(self._stderr).decode("utf-8", errors="replace").strip()
            code = (
                "authentication_cancelled"
                if process.returncode == 1
                else "session_ended"
            )
            self._fail(
                PrivilegedProcessError(
                    code,
                    details
                    or f"Privileged session exited with code {process.returncode}",
                )
            )

    def _fail(self, error: PrivilegedProcessError) -> None:
        with self._state_condition:
            if self._failure is None:
                self._failure = error
            self._state_condition.notify_all()
        with self._pending_lock:
            pending_requests = list(self._pending.values())
        for pending in pending_requests:
            with pending.condition:
                pending.error = error
                pending.condition.notify_all()
        with self._state_condition:
            process = self._process
            should_terminate = (
                not self._closed
                and process is not None
                and process.poll() is None
                and error.code == "protocol_error"
            )
        if should_terminate:
            threading.Thread(
                target=self._terminate, args=(process,), daemon=True
            ).start()

    def _terminate(self, process: subprocess.Popen[bytes]) -> None:
        if process.poll() is not None:
            return
        try:
            os.killpg(process.pid, signal.SIGTERM)
            process.wait(timeout=TERMINATION_TIMEOUT)
        except ProcessLookupError:
            return
        except subprocess.TimeoutExpired:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                return
            process.wait()

    def close(self) -> None:
        with self._state_condition:
            if self._closed:
                return
            self._closed = True
            process = self._process
        self._fail(
            PrivilegedProcessError("session_closed", "Privileged session closed")
        )
        if process is None:
            return
        if process.poll() is None and self._session_ready:
            request_id = uuid.uuid4().hex
            pending = _PendingRequest()
            with self._pending_lock:
                self._pending[request_id] = pending
            try:
                self._send(
                    {"request_id": request_id, "operation": "shutdown", "arguments": {}}
                )
                process.wait(timeout=TERMINATION_TIMEOUT)
            except (PrivilegedProcessError, subprocess.TimeoutExpired):
                self._terminate(process)
            finally:
                with self._pending_lock:
                    self._pending.pop(request_id, None)
        else:
            self._terminate(process)
