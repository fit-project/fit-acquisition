from __future__ import annotations

from pathlib import Path

import pytest

from fit_acquisition.tasks.tasks_handler import TasksHandler
from fit_acquisition.tasks.tasks_manager import TasksManager


class _Logger:
    def __init__(self) -> None:
        self.messages: list[str] = []

    def info(self, message: str) -> None:
        self.messages.append(message)


@pytest.mark.e2e
def test_tasks_manager_discovers_and_initializes_task_from_package(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    package_root = tmp_path / "fake_tasks"
    package_root.mkdir()
    (package_root / "__init__.py").write_text("", encoding="utf-8")
    (package_root / "demo.py").write_text(
        "\n".join(
            [
                "from fit_acquisition.tasks.task import Task",
                "",
                "class TaskFake(Task):",
                "    def __init__(self, logger, progress_bar=None, status_bar=None):",
                "        super().__init__(logger, progress_bar, status_bar, label='FAKE')",
                "    def start(self):",
                "        return None",
            ]
        ),
        encoding="utf-8",
    )

    monkeypatch.syspath_prepend(str(tmp_path))

    handler = TasksHandler()
    handler.clear_tasks()

    manager = TasksManager()
    manager.clear_tasks()
    manager.class_names_modules.clear()
    manager.task_package_names.clear()

    manager.register_task_package("fake_tasks")
    manager.load_all_task_modules()
    manager.init_tasks(["TaskFake"], _Logger(), None, None)

    task = manager.get_task("TaskFake")

    assert task is not None
    assert task.label

    manager.clear_tasks()
