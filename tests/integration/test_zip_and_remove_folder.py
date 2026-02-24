from __future__ import annotations

import pytest

from fit_common.core import AcquisitionType
from fit_acquisition.tasks.post_acquisition import zip_and_remove_folder as zip_module


@pytest.mark.integration
def test_zip_worker_archives_and_removes(monkeypatch: pytest.MonkeyPatch) -> None:
    worker = zip_module.ZipAndRemoveFolderWorker()
    worker.options = {
        "type": AcquisitionType.WEB,
        "acquisition_directory": "/tmp/acq",
    }

    calls: dict[str, list[str]] = {"archive": [], "rmtree": []}

    monkeypatch.setattr(zip_module.os.path, "isdir", lambda path: True)
    monkeypatch.setattr(zip_module.os, "listdir", lambda path: ["one"])
    monkeypatch.setattr(
        zip_module.shutil,
        "make_archive",
        lambda base, fmt, root: calls["archive"].append(base),
    )
    monkeypatch.setattr(
        zip_module.shutil,
        "rmtree",
        lambda path: calls["rmtree"].append(path),
    )

    events: list[str] = []
    worker.started.connect(lambda: events.append("started"))
    worker.finished.connect(lambda: events.append("finished"))

    worker.start()

    assert events == ["started", "finished"]
    assert "/tmp/acq/downloads" in calls["archive"]
    assert "/tmp/acq/screenshot" in calls["archive"]
    assert "/tmp/acq/downloads" in calls["rmtree"]
    assert "/tmp/acq/screenshot" in calls["rmtree"]


@pytest.mark.integration
def test_task_zip_start_delegates(monkeypatch: pytest.MonkeyPatch) -> None:
    class _Logger:
        def info(self, message: str) -> None:
            return None

    task = zip_module.TaskZipAndRemoveFolder(_Logger())
    calls: list[str] = []
    monkeypatch.setattr(zip_module.Task, "start_task", lambda self, msg: calls.append(msg))

    task.start()

    assert calls == [task.translations["ZIP_AND_REMOVE_FOLDER_STARTED"]]
