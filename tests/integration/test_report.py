from __future__ import annotations

from types import SimpleNamespace

import pytest

from fit_acquisition.tasks.post_acquisition import report as report_module


class _Logger:
    def __init__(self) -> None:
        self.messages: list[str] = []

    def info(self, message: str) -> None:
        self.messages.append(message)


@pytest.mark.integration
def test_report_worker_builds_pdf_with_monkeypatch(monkeypatch: pytest.MonkeyPatch) -> None:
    worker = report_module.ReportWorker()
    worker.options = {
        "acquisition_directory": "/tmp/acq",
        "type": "web",
        "case_info": {"name": "Case", "proceeding_type": 2},
    }

    captured: dict[str, object] = {}

    class _FakeBuilder:
        def __init__(self, report_type, **kwargs):
            captured["report_type"] = report_type
            captured["kwargs"] = kwargs
            self.acquisition_type = None
            self.ntp = None

        def generate_pdf(self) -> None:
            captured["generated"] = True

    monkeypatch.setattr(report_module, "PdfReportBuilder", _FakeBuilder)
    monkeypatch.setattr(report_module, "get_language", lambda: "English")
    monkeypatch.setattr(report_module, "load_translations", lambda *args, **kwargs: {"x": "y"})
    monkeypatch.setattr(report_module, "ScreenRecorderController", lambda: SimpleNamespace(configuration={"filename": "scr.mp4"}))
    monkeypatch.setattr(report_module, "PacketCaptureController", lambda: SimpleNamespace(configuration={"filename": "cap.pcap"}))
    monkeypatch.setattr(report_module, "LegalProceedingTypeController", lambda: SimpleNamespace(get_proceeding_name_by_id=lambda _: "Penale"))
    monkeypatch.setattr(report_module, "NetworkCheckController", lambda: SimpleNamespace(configuration={"ntp_server": "pool.ntp.org"}))
    monkeypatch.setattr(report_module, "get_ntp_date_and_time", lambda server: "2026-01-01T00:00:00Z")

    events: list[str] = []
    worker.started.connect(lambda: events.append("started"))
    worker.finished.connect(lambda: events.append("finished"))

    worker.start()

    assert events == ["started", "finished"]
    assert captured["generated"] is True
    assert captured["kwargs"]["filename"] == "acquisition_report.pdf"


@pytest.mark.integration
def test_task_report_start_delegates(monkeypatch: pytest.MonkeyPatch) -> None:
    task = report_module.TaskReport(_Logger())
    calls: list[str] = []
    monkeypatch.setattr(report_module.Task, "start_task", lambda self, msg: calls.append(msg))

    task.start()

    assert calls == [task.translations["GENERATE_PDF_REPORT_STARTED"]]
