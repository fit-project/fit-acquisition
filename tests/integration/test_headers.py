from __future__ import annotations

import pytest

from fit_acquisition.tasks.network_tools import headers as headers_module


class _Logger:
    def __init__(self) -> None:
        self.messages: list[str] = []

    def info(self, message: str) -> None:
        self.messages.append(message)


@pytest.mark.integration
def test_headers_worker_success(monkeypatch: pytest.MonkeyPatch) -> None:
    worker = headers_module.HeadersWorker()
    worker.options = {"url": "https://example.org"}
    worker.logger = _Logger()

    class _Response:
        headers = {"Server": "nginx", "X-Test": "1"}

        def raise_for_status(self) -> None:
            return None

    monkeypatch.setattr(headers_module.requests, "get", lambda *args, **kwargs: _Response())

    events: list[str] = []
    worker.started.connect(lambda: events.append("started"))
    worker.finished.connect(lambda: events.append("finished"))

    worker.start()

    assert events == ["started", "finished"]
    assert any("Server: nginx" in msg for msg in worker.logger.messages)


@pytest.mark.integration
def test_headers_worker_uses_tls_verification_by_default(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    worker = headers_module.HeadersWorker()
    worker.options = {"url": "https://example.org"}

    class _Response:
        headers = {"Server": "nginx"}

        def raise_for_status(self) -> None:
            return None

    captured: dict[str, object] = {}

    def _fake_get(*args, **kwargs):
        captured["verify"] = kwargs.get("verify")
        return _Response()

    monkeypatch.setattr(headers_module.requests, "get", _fake_get)

    worker.start()

    assert captured["verify"] is True


@pytest.mark.integration
def test_headers_worker_allows_explicit_tls_disable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    worker = headers_module.HeadersWorker()
    worker.options = {"url": "https://example.org", "verify_tls": False}

    class _Response:
        headers = {"Server": "nginx"}

        def raise_for_status(self) -> None:
            return None

    captured: dict[str, object] = {}

    def _fake_get(*args, **kwargs):
        captured["verify"] = kwargs.get("verify")
        return _Response()

    monkeypatch.setattr(headers_module.requests, "get", _fake_get)

    worker.start()

    assert captured["verify"] is False


@pytest.mark.integration
def test_task_headers_start_uses_translation(monkeypatch: pytest.MonkeyPatch) -> None:
    task = headers_module.TaskHeaders(_Logger())
    calls: list[str] = []
    monkeypatch.setattr(headers_module.Task, "start_task", lambda self, msg: calls.append(msg))

    task.start()

    assert calls == [task.translations["HEADERS_STARTED"]]
