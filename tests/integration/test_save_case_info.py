from __future__ import annotations
from unittest.mock import mock_open

import pytest

from fit_acquisition.tasks.post_acquisition import save_case_info as save_module


@pytest.mark.integration
def test_save_case_info_worker_serializes_logo_bin(monkeypatch: pytest.MonkeyPatch) -> None:
    worker = save_module.SaveCaseInfoWorker()
    original_logo = b"bin-logo"
    payload = {"name": "Case", "logo_bin": original_logo}
    worker.options = {"acquisition_directory": "/tmp/acq", "case_info": payload}

    mocked_open = mock_open()
    dumped: dict[str, object] = {}
    monkeypatch.setattr("builtins.open", mocked_open)
    monkeypatch.setattr(save_module.json, "dump", lambda data, fp, ensure_ascii=False: dumped.setdefault("data", data.copy()))

    events: list[str] = []
    worker.started.connect(lambda: events.append("started"))
    worker.finished.connect(lambda: events.append("finished"))

    worker.start()

    assert events == ["started", "finished"]
    assert dumped["data"]["logo_bin"] != original_logo
    assert payload["logo_bin"] == original_logo


@pytest.mark.integration
def test_task_save_case_info_start_delegates(monkeypatch: pytest.MonkeyPatch) -> None:
    class _Logger:
        def info(self, message: str) -> None:
            return None

    task = save_module.TaskSaveCaseInfo(_Logger())
    calls: list[str] = []
    monkeypatch.setattr(save_module.Task, "start_task", lambda self, msg: calls.append(msg))

    task.start()

    assert calls == [task.translations["SAVE_CASE_INFO_STARTED"]]
