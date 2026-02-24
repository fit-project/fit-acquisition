from __future__ import annotations

from types import SimpleNamespace

import pytest

from fit_acquisition.tasks.post_acquisition.pec import pec_and_download_eml as pec_module


class _Logger:
    def __init__(self) -> None:
        self.messages: list[str] = []

    def info(self, message: str) -> None:
        self.messages.append(message)


@pytest.mark.integration
def test_pec_worker_start_and_download_emit(monkeypatch: pytest.MonkeyPatch) -> None:
    worker = pec_module.PecAndDownloadEmlWorker()
    worker.options = {
        "pec_email": "a@example.org",
        "password": "x",
        "type": "web",
        "case_info": {"name": "case"},
        "acquisition_directory": "/tmp/acq",
        "smtp_server": "smtp.example.org",
        "smtp_port": 465,
        "imap_server": "imap.example.org",
        "imap_port": 993,
        "retries": 1,
    }

    class _Pec:
        def __init__(self, *args, **kwargs) -> None:
            return None

        def send_pec(self) -> None:
            return None

        def retrieve_eml(self) -> bool:
            return True

    monkeypatch.setattr(pec_module, "Pec", _Pec)
    monkeypatch.setattr(pec_module, "QEventLoop", lambda: SimpleNamespace(exec=lambda: None, quit=lambda: None))
    monkeypatch.setattr(pec_module.QTimer, "singleShot", lambda ms, fn: fn())

    events: list[str] = []
    worker.started.connect(lambda: events.append("started"))
    worker.sentpec.connect(lambda: events.append("sent"))
    worker.downloadedeml.connect(lambda: events.append("downloaded"))

    worker.start()
    worker.download_eml()

    assert events == ["started", "sent", "downloaded"]


@pytest.mark.integration
def test_task_pec_options_use_controller(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        pec_module,
        "PecController",
        lambda: SimpleNamespace(
            configuration={
                "pec_email": "a@example.org",
                "password": "x",
                "smtp_server": "smtp.example.org",
                "smtp_port": 465,
                "imap_server": "imap.example.org",
                "imap_port": 993,
                "retries": 1,
            }
        ),
    )

    task = pec_module.TaskPecAndDownloadEml(_Logger())
    task.options = {
        "acquisition_directory": "/tmp/acq",
        "case_info": {"name": "case"},
        "type": "web",
    }

    assert task.options["acquisition_directory"] == "/tmp/acq"
    assert task.options["type"] == "web"
