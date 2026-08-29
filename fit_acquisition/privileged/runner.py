from __future__ import annotations

import os
import shutil
import signal
import subprocess
import sys
import threading
import time
from pathlib import Path


READY_MARKER = b"FIT_PRIVILEGED_READY"
DEFAULT_READINESS_TIMEOUT = 60.0
TERMINATION_TIMEOUT = 5.0


class PrivilegedProcessError(RuntimeError):
    def __init__(self, code: str, details: str):
        super().__init__(details)
        self.code = code
        self.details = details

    def as_error(self) -> dict[str, str]:
        return {"code": self.code, "details": self.details}


class PrivilegedRunner:
    ACTIONS = {"packet-capture", "traceroute"}

    def __init__(self) -> None:
        self._process: subprocess.Popen[bytes] | None = None
        self._condition = threading.Condition()
        self._ready = False
        self._finished = False
        self._stdout = bytearray()
        self._stderr = bytearray()

    @property
    def active(self) -> bool:
        with self._condition:
            return self._process is not None and not self._finished

    @staticmethod
    def _environment() -> dict[str, str]:
        askpass = os.environ.get("FIT_LINUX_SUDO_ASKPASS")
        if not askpass:
            raise PrivilegedProcessError(
                "askpass_missing", "FIT_LINUX_SUDO_ASKPASS is not configured"
            )
        if not Path(askpass).is_file():
            raise PrivilegedProcessError(
                "askpass_missing",
                "The configured Linux askpass helper does not exist",
            )
        env = os.environ.copy()
        env["SUDO_ASKPASS"] = askpass
        for name in ("FIT_LINUX_ASKPASS_PYTHON", "FIT_LINUX_ASKPASS_BUNDLED"):
            if name in os.environ:
                env[name] = os.environ[name]
        return env

    @classmethod
    def command(cls, action: str, arguments: list[str]) -> list[str]:
        if sys.platform != "linux":
            raise PrivilegedProcessError(
                "unsupported_platform", "Privileged helpers are Linux-only"
            )
        if action not in cls.ACTIONS:
            raise PrivilegedProcessError("invalid_action", "Unsupported privileged action")
        sudo = shutil.which("sudo")
        if sudo is None:
            raise PrivilegedProcessError("sudo_missing", "sudo is not available")
        return [
            sudo,
            "-A",
            sys.executable,
            "-m",
            "fit_acquisition.privileged.cli",
            action,
            *arguments,
        ]

    def start(
        self,
        action: str,
        arguments: list[str],
        readiness_timeout: float = DEFAULT_READINESS_TIMEOUT,
    ) -> None:
        command = self.command(action, arguments)
        env = self._environment()
        with self._condition:
            if self._process is not None:
                raise PrivilegedProcessError(
                    "already_started", "Privileged process is already running"
                )
            self._ready = False
            self._finished = False
            self._stdout.clear()
            self._stderr.clear()
            self._process = subprocess.Popen(
                command,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=env,
                shell=False,
                start_new_session=True,
            )
            process = self._process

        assert process.stdout is not None
        assert process.stderr is not None
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

        try:
            self._wait_for_ready(process, readiness_timeout)
        except Exception:
            self.cancel()
            self._wait_for_exit(process, TERMINATION_TIMEOUT, force=True)
            self._clear_process(process)
            raise

    def _read_stdout(self, process: subprocess.Popen[bytes]) -> None:
        assert process.stdout is not None
        while chunk := process.stdout.read(64 * 1024):
            with self._condition:
                self._stdout.extend(chunk)

    def _read_stderr(self, process: subprocess.Popen[bytes]) -> None:
        assert process.stderr is not None
        for line in iter(process.stderr.readline, b""):
            if line.rstrip(b"\r\n") == READY_MARKER:
                with self._condition:
                    if self._process is process:
                        self._ready = True
                        self._condition.notify_all()
                continue
            with self._condition:
                self._stderr.extend(line)

    def _watch(
        self,
        process: subprocess.Popen[bytes],
        stdout_reader: threading.Thread,
        stderr_reader: threading.Thread,
    ) -> None:
        process.wait()
        stdout_reader.join()
        stderr_reader.join()
        with self._condition:
            if self._process is process:
                self._finished = True
                self._condition.notify_all()

    def _wait_for_ready(self, process: subprocess.Popen[bytes], timeout: float) -> None:
        deadline = time.monotonic() + timeout
        with self._condition:
            while not self._ready and not self._finished:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise PrivilegedProcessError(
                        "readiness_timeout", "Privileged process readiness timed out"
                    )
                self._condition.wait(remaining)
            if self._ready:
                return
            self._raise_process_failure(process, before_ready=True)

    def _diagnostics(self) -> str:
        with self._condition:
            return bytes(self._stderr).decode("utf-8", errors="replace").strip()

    def _raise_process_failure(
        self, process: subprocess.Popen[bytes], *, before_ready: bool = False
    ) -> None:
        details = self._diagnostics()
        returncode = process.returncode
        if returncode == 0 and before_ready:
            code = "readiness_missing"
            fallback = "Privileged process exited before reporting readiness"
        else:
            code = (
                "authentication_cancelled"
                if returncode == 1 and "sudo" in details.lower()
                else "process_failed"
            )
            fallback = f"Privileged process exited with code {returncode}"
        raise PrivilegedProcessError(code, details or fallback)

    def _wait_for_exit(
        self,
        process: subprocess.Popen[bytes],
        timeout: float | None,
        *,
        force: bool = False,
    ) -> bool:
        deadline = None if timeout is None else time.monotonic() + timeout
        with self._condition:
            while not self._finished:
                remaining = None if deadline is None else deadline - time.monotonic()
                if remaining is not None and remaining <= 0:
                    break
                self._condition.wait(remaining)
            finished = self._finished
        if not finished and force:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            with self._condition:
                while not self._finished:
                    self._condition.wait()
            return True
        return finished

    def _clear_process(self, process: subprocess.Popen[bytes]) -> None:
        with self._condition:
            if self._process is process:
                self._process = None

    def wait(self, timeout: float | None = None) -> bytes:
        with self._condition:
            process = self._process
        if process is None:
            raise PrivilegedProcessError("not_started", "Privileged process was not started")

        if not self._wait_for_exit(process, timeout):
            self.cancel()
            self._wait_for_exit(process, TERMINATION_TIMEOUT, force=True)
            self._clear_process(process)
            raise PrivilegedProcessError("timeout", "Privileged process timed out")

        self._clear_process(process)
        if process.returncode != 0:
            self._raise_process_failure(process)
        with self._condition:
            return bytes(self._stdout)

    def cancel(self) -> None:
        with self._condition:
            process = self._process
            finished = self._finished
        if process is None or finished or process.poll() is not None:
            return
        try:
            os.killpg(process.pid, signal.SIGTERM)
        except ProcessLookupError:
            return
        self._wait_for_exit(process, TERMINATION_TIMEOUT, force=True)
