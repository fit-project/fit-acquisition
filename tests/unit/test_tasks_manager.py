from __future__ import annotations

import pytest

from fit_acquisition.tasks import tasks_manager as manager_module


@pytest.mark.unit
def test_register_task_package_accepts_only_strings() -> None:
    manager = manager_module.TasksManager()
    manager.task_package_names.clear()

    manager.register_task_package("fit_acquisition.tasks.network_tools")
    manager.register_task_package(123)  # type: ignore[arg-type]

    assert manager.task_package_names == ["fit_acquisition.tasks.network_tools"]

@pytest.mark.unit
def test_get_tasks_from_class_name_returns_existing_only() -> None:
    manager = manager_module.TasksManager()
    manager.clear_tasks()

    class _TaskA:
        pass

    class _TaskB:
        pass

    a = _TaskA()
    b = _TaskB()
    manager.task_handler.add_task(a)
    manager.task_handler.add_task(b)

    found = manager.get_tasks_from_class_name(["_TaskA", "Missing", "_TaskB"])

    assert found == [a, b]
