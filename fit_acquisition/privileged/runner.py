from __future__ import annotations

import os
import shutil
import signal
import subprocess
import sys
import threading
from pathlib import Path


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
        self._lock = threading.Lock()

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

    def start(self, action: str, arguments: list[str]) -> None:
        command = self.command(action, arguments)
        env = self._environment()
        with self._lock:
            self._process = subprocess.Popen(
                command,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=env,
                shell=False,
                start_new_session=True,
            )

    def wait(self, timeout: float | None = None) -> bytes:
        with self._lock:
            process = self._process
        if process is None:
            raise PrivilegedProcessError("not_started", "Privileged process was not started")
        try:
            stdout, stderr = process.communicate(timeout=timeout)
        except subprocess.TimeoutExpired as exc:
            self.cancel()
            try:
                stdout, stderr = process.communicate(timeout=5)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                process.communicate()
            raise PrivilegedProcessError("timeout", "Privileged process timed out") from exc
        finally:
            with self._lock:
                self._process = None
        if process.returncode != 0:
            details = stderr.decode("utf-8", errors="replace").strip()
            code = (
                "authentication_cancelled"
                if process.returncode == 1 and "sudo" in details.lower()
                else "process_failed"
            )
            raise PrivilegedProcessError(
                code,
                details
                or f"Privileged process exited with code {process.returncode}",
            )
        return stdout

    def cancel(self) -> None:
        with self._lock:
            process = self._process
        if process is None or process.poll() is not None:
            return
        try:
            os.killpg(process.pid, signal.SIGTERM)
        except ProcessLookupError:
            return
