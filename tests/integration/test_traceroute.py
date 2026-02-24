from __future__ import annotations

from unittest.mock import mock_open

import pytest

from fit_acquisition.tasks.network_tools import traceroute as traceroute_module


@pytest.mark.integration
def test_traceroute_worker_writes_lines(monkeypatch: pytest.MonkeyPatch) -> None:
    worker = traceroute_module.TracerouteWorker()
    worker.options = {
        "url": "https://example.org",
        "acquisition_directory": "/tmp/acq",
    }

    class _FakeTCP:
        def __init__(self, *args, **kwargs) -> None:
            return None

    class _FakeIP:
        def __truediv__(self, other):
            return self

    class _Snd:
        ttl = 7

    class _Rcv:
        src = "1.2.3.4"
        payload = _FakeTCP()

    monkeypatch.setattr(traceroute_module.scapy, "TCP", _FakeTCP)
    monkeypatch.setattr(traceroute_module.scapy, "IP", lambda **kwargs: _FakeIP())
    monkeypatch.setattr(traceroute_module.scapy, "RandShort", lambda: 11)
    monkeypatch.setattr(traceroute_module.scapy, "sr", lambda *a, **k: ([(_Snd(), _Rcv())], []))
    mocked_open = mock_open()
    monkeypatch.setattr("builtins.open", mocked_open)

    events: list[str] = []
    worker.started.connect(lambda: events.append("started"))
    worker.finished.connect(lambda: events.append("finished"))

    worker.start()

    assert events == ["started", "finished"]
    handle = mocked_open()
    handle.write.assert_called()


@pytest.mark.integration
def test_task_traceroute_start_uses_translation(monkeypatch: pytest.MonkeyPatch) -> None:
    class _Logger:
        def info(self, message: str) -> None:
            return None

    task = traceroute_module.TaskTraceroute(_Logger())
    calls: list[str] = []
    monkeypatch.setattr(traceroute_module.Task, "start_task", lambda self, msg: calls.append(msg))

    task.start()

    assert calls == [task.translations["TRACEROUTE_STARTED"]]
