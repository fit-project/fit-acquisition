from __future__ import annotations

import subprocess
import threading
import time

import pytest
from PySide6 import QtWidgets

from fit_acquisition.tasks.infinite_loop import screen_recorder as screen_module
from fit_acquisition.tasks.network_tools import headers as headers_module
from fit_acquisition.tasks.network_tools import nslookup as nslookup_module
from fit_acquisition.tasks.network_tools import whois as whois_module


@pytest.mark.unit
@pytest.mark.parametrize(
    ("worker_cls", "options"),
    [
        (headers_module.HeadersWorker, {"url": "not-a-url"}),
        (
            nslookup_module.NslookupWorker,
            {
                "url": "not-a-url",
                "nslookup_dns_server": "1.1.1.1",
                "nslookup_enable_verbose_mode": False,
                "nslookup_enable_tcp": False,
            },
        ),
        (whois_module.WhoisWorker, {"url": "###"}),
    ],
)
def test_workers_emit_error_payload_on_invalid_input(worker_cls, options) -> None:
    worker = worker_cls()
    worker.options = options

    errors: list[dict] = []
    worker.error.connect(lambda payload: errors.append(payload))

    worker.start()

    assert len(errors) == 1
    payload = errors[0]
    assert {"title", "message", "details"}.issubset(payload)
    assert isinstance(payload["message"], str)
    assert isinstance(payload["details"], str)


@pytest.mark.unit
def test_screen_recorder_emits_error_when_binary_is_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    worker = screen_module.ScreenRecorderWorker()
    worker.options = {
        "acquisition_directory": "/tmp/acq",
        "filename": "/tmp/acq/screenrecorder",
    }
    monkeypatch.delenv("FIT_SCREEN_RECODER_PATH", raising=False)

    errors: list[dict] = []
    worker.error.connect(lambda payload: errors.append(payload))

    worker.start()

    assert len(errors) == 1
    payload = errors[0]
    assert payload["details"]
    assert "fit-screen-recorder" in payload["details"]
    assert "path" in payload["details"].lower()


class _FakeStdin:
    def __init__(self, process: "_FakeProcess") -> None:
        self._process = process
        self.writes: list[str] = []
        self.flush_count = 0

    def write(self, value: str) -> None:
        self.writes.append(value)
        if value == "stop\n":
            self._process.finish()

    def flush(self) -> None:
        self.flush_count += 1


class _FakeProcess:
    def __init__(
        self,
        *,
        stdout_lines: list[str] | None = None,
        stderr_lines: list[str] | None = None,
        returncode: int = 0,
    ) -> None:
        self.stdout = iter(stdout_lines or [])
        self.stderr = iter(stderr_lines or [])
        self.stdin = _FakeStdin(self)
        self.returncode = None
        self._final_returncode = returncode
        self._finished = threading.Event()
        self.terminate_calls = 0

    def poll(self) -> int | None:
        return self.returncode

    def wait(self, timeout: float | None = None) -> int:
        if not self._finished.wait(timeout):
            raise subprocess.TimeoutExpired(cmd="fit-screen-recorder", timeout=timeout)
        self.returncode = self._final_returncode
        return self.returncode

    def terminate(self) -> None:
        self.terminate_calls += 1
        self.finish()

    def kill(self) -> None:
        self.finish()

    def finish(self) -> None:
        self.returncode = self._final_returncode
        self._finished.set()


@pytest.mark.unit
def test_screen_recorder_starts_and_stops_external_binary(
    qapp: QtWidgets.QApplication,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    worker = screen_module.ScreenRecorderWorker()
    worker.options = {
        "acquisition_directory": "/tmp/acq",
        "filename": "/tmp/acq/screenrecorder",
    }

    fake_process = _FakeProcess(stdout_lines=["backend=mac\n", "runner=ready\n"])
    popen_calls: list[list[str]] = []
    monkeypatch.setenv("FIT_SCREEN_RECODER_PATH", "/tmp/bin/fit-screen-recorder")

    def _fake_popen(command, **_kwargs):
        popen_calls.append(command)
        return fake_process

    monkeypatch.setattr(screen_module.subprocess, "Popen", _fake_popen)
    started: list[bool] = []
    finished: list[bool] = []
    errors: list[dict] = []
    worker.started.connect(lambda: started.append(True))
    worker.finished.connect(lambda: finished.append(True))
    worker.error.connect(lambda payload: errors.append(payload))

    worker.start()

    timeout = time.time() + 1
    while not started and time.time() < timeout:
        qapp.processEvents()
        time.sleep(0.01)

    worker.stop()

    timeout = time.time() + 1
    while not finished and time.time() < timeout:
        qapp.processEvents()
        time.sleep(0.01)

    assert popen_calls == [[
        "/tmp/bin/fit-screen-recorder",
        "--output",
        "/tmp/acq/screenrecorder.mp4",
        "--stdin-control",
        "--no-audio",
    ]]
    assert started == [True]
    assert finished == [True]
    assert errors == []
    assert fake_process.stdin.writes == ["stop\n"]
    assert fake_process.stdin.flush_count == 1
