from __future__ import annotations

import importlib
import inspect
import pkgutil

import pytest

from fit_acquisition.tasks.task import Task



def _iter_task_classes():
    import fit_acquisition.tasks as tasks_pkg

    prefix = tasks_pkg.__name__ + "."
    for module_info in pkgutil.walk_packages(tasks_pkg.__path__, prefix):
        module = importlib.import_module(module_info.name)
        for _, cls in inspect.getmembers(module, inspect.isclass):
            if not issubclass(cls, Task) or cls is Task:
                continue
            if cls.__module__ != module.__name__:
                continue
            yield cls


@pytest.mark.contract
def test_all_task_classes_follow_contract() -> None:
    classes = list(_iter_task_classes())

    assert classes, "No Task subclasses discovered"

    for cls in classes:
        assert getattr(cls, "__is_task__", False) is True
        assert callable(getattr(cls, "start", None))
        signature = inspect.signature(cls.__init__)
        assert "logger" in signature.parameters
