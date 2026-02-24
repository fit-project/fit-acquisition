from __future__ import annotations

from types import SimpleNamespace

import pytest

from fit_acquisition.tasks.post_acquisition import hash as hash_module


class _Logger:
    def __init__(self) -> None:
        self.messages: list[str] = []

    def info(self, message: str) -> None:
        self.messages.append(message)


@pytest.mark.integration
def test_hash_worker_logs_hashes_without_real_files(monkeypatch: pytest.MonkeyPatch) -> None:
    worker = hash_module.HashWorker()
    worker.logger = _Logger()
    worker.options = {"acquisition_directory": "/tmp/acq", "exclude_list": []}

    fake_entries = [SimpleNamespace(name="a.txt", is_file=lambda: True), SimpleNamespace(name="acquisition.log", is_file=lambda: True)]
    monkeypatch.setattr(hash_module.os, "scandir", lambda path: fake_entries)
    monkeypatch.setattr(hash_module.os, "stat", lambda path: SimpleNamespace(st_size=12))
    monkeypatch.setattr(
        worker,
        "_HashWorker__calculate_hash",
        lambda filename, algorithm: f"{algorithm}-digest",
    )

    events: list[str] = []
    worker.started.connect(lambda: events.append("started"))
    worker.finished.connect(lambda: events.append("finished"))

    worker.start()

    assert events == ["started", "finished"]
    assert any("MD5: md5-digest" in m for m in worker.logger.messages)


@pytest.mark.integration
def test_task_hash_options_sets_exclude_list() -> None:
    task = hash_module.TaskHash(_Logger())
    task.options = {
        "acquisition_directory": "/tmp/acq",
        "exclude_from_hash_calculation": ["keep.me"],
    }

    assert task.options["exclude_list"] == ["keep.me"]
