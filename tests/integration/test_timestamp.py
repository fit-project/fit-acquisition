from __future__ import annotations

import io

import pytest

from fit_acquisition.tasks.post_acquisition import timestamp as timestamp_module


@pytest.mark.integration
def test_timestamp_worker_happy_path_without_files(monkeypatch: pytest.MonkeyPatch) -> None:
    worker = timestamp_module.TimestampWorker()
    worker.options = {
        "acquisition_directory": "/tmp/acq",
        "pdf_filename": "acquisition_report.pdf",
        "cert_url": "https://tsa.example/cert",
        "server_name": "https://tsa.example",
    }

    class _Resp:
        content = b"cert-data"

        def raise_for_status(self) -> None:
            return None

    class _Ts:
        def __init__(self, *args, **kwargs) -> None:
            return None

        def timestamp(self, data: bytes) -> bytes:
            return b"tsr-bytes"

    monkeypatch.setattr(timestamp_module.requests, "get", lambda *a, **k: _Resp())
    monkeypatch.setattr(timestamp_module, "RemoteTimestamper", _Ts)

    def _fake_open(path: str, mode: str):
        if "b" in mode:
            return io.BytesIO(b"pdf-bytes" if "acquisition_report.pdf" in path else b"")
        return io.StringIO("")

    monkeypatch.setattr("builtins.open", _fake_open)

    events: list[str] = []
    worker.started.connect(lambda: events.append("started"))
    worker.finished.connect(lambda: events.append("finished"))

    worker.start()

    assert events == ["started", "finished"]


@pytest.mark.integration
def test_task_timestamp_options_use_controller(monkeypatch: pytest.MonkeyPatch) -> None:
    class _Logger:
        def info(self, message: str) -> None:
            return None

    monkeypatch.setattr(
        timestamp_module,
        "TimestampController",
        lambda: type("_C", (), {"configuration": {"cert_url": "u", "server_name": "s"}})(),
    )

    task = timestamp_module.TaskTimestamp(_Logger())
    task.options = {"acquisition_directory": "/tmp/acq", "pdf_filename": "x.pdf"}

    assert task.options["acquisition_directory"] == "/tmp/acq"
    assert task.options["pdf_filename"] == "x.pdf"
    assert task.options["server_name"] == "s"
