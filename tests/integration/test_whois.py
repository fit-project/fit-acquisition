from __future__ import annotations

import pytest

from fit_acquisition.tasks.network_tools import whois as whois_module


class _Logger:
    def __init__(self) -> None:
        self.messages: list[str] = []

    def info(self, message: str) -> None:
        self.messages.append(message)


@pytest.mark.integration
def test_whois_worker_success(monkeypatch: pytest.MonkeyPatch) -> None:
    worker = whois_module.WhoisWorker()
    worker.logger = _Logger()
    worker.options = {"url": "example.org"}

    monkeypatch.setattr(whois_module, "extract_domain", lambda value: "example.org")

    class _Client:
        def whois_lookup(self, a, domain, flags):
            assert domain == "example.org"
            return "WHOIS DATA"

    monkeypatch.setattr(whois_module, "NICClient", _Client)

    events: list[str] = []
    worker.started.connect(lambda: events.append("started"))
    worker.finished.connect(lambda: events.append("finished"))

    worker.start()

    assert events == ["started", "finished"]
    assert worker.logger.messages == ["WHOIS DATA"]
