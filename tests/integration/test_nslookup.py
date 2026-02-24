from __future__ import annotations

from types import SimpleNamespace

import pytest

from fit_acquisition.tasks.network_tools import nslookup as nslookup_module


class _Logger:
    def __init__(self) -> None:
        self.messages: list[str] = []

    def info(self, message: str) -> None:
        self.messages.append(message)


@pytest.mark.integration
def test_nslookup_worker_success(monkeypatch: pytest.MonkeyPatch) -> None:
    worker = nslookup_module.NslookupWorker()
    worker.logger = _Logger()
    worker.options = {
        "url": "https://example.org",
        "nslookup_dns_server": "1.1.1.1",
        "nslookup_enable_verbose_mode": False,
        "nslookup_enable_tcp": False,
    }

    class _Query:
        def __init__(self, **kwargs) -> None:
            self.kwargs = kwargs

        def dns_lookup(self, netloc: str):
            assert netloc == "example.org"
            return SimpleNamespace(response_full=["line1", "line2"])

    monkeypatch.setattr(nslookup_module, "Nslookup", _Query)

    events: list[str] = []
    worker.started.connect(lambda: events.append("started"))
    worker.finished.connect(lambda: events.append("finished"))

    worker.start()

    assert events == ["started", "finished"]
    assert worker.logger.messages == ["line1\nline2"]


@pytest.mark.integration
def test_task_nslookup_options_uses_controller(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        nslookup_module,
        "NetworkCheckController",
        lambda: SimpleNamespace(
            configuration={
                "nslookup_dns_server": "8.8.8.8",
                "nslookup_enable_verbose_mode": True,
                "nslookup_enable_tcp": True,
            }
        ),
    )

    task = nslookup_module.TaskNslookup(_Logger())
    task.options = {"url": "https://example.org"}

    assert task.options["url"] == "https://example.org"
    assert task.options["nslookup_dns_server"] == "8.8.8.8"
