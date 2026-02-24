from __future__ import annotations

from datetime import timedelta

import pytest
from fit_common.gui.utils import State, Status
from PySide6 import QtCore

from fit_acquisition.tasks.tasks_handler import TasksHandler
from fit_acquisition.tasks.tasks_info import TasksInfo


class _FakeTask(QtCore.QObject):
    started = QtCore.Signal()
    finished = QtCore.Signal()

    def __init__(self, label: str):
        super().__init__()
        self.label = label
        self.status = Status.SUCCESS
        self.details = ""
        self.state = State.INITIALIZATED

    def is_active(self):
        return self.state != State.COMPLETED

    def get_elapsed_time(self):
        return timedelta(seconds=1)


@pytest.mark.e2e
def test_tasks_info_logs_start_and_finish(
    qapp, monkeypatch: pytest.MonkeyPatch
) -> None:
    handler = TasksHandler()
    handler.clear_tasks()

    fake_task = _FakeTask("FakeTask")
    handler.add_task(fake_task)

    monkeypatch.setattr(QtCore.QTimer, "singleShot", lambda _ms, fn: fn())

    dialog = TasksInfo()

    fake_task.state = State.STARTED
    fake_task.started.emit()

    fake_task.state = State.COMPLETED
    fake_task.finished.emit()

    qapp.processEvents()

    content = dialog.ui.task_log_text.toPlainText()
    assert "FakeTask started" in content
    assert "FakeTask finished" in content

    handler.clear_tasks()
