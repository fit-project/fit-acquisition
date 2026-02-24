from __future__ import annotations

import importlib
import inspect
import pkgutil

import pytest
from PySide6.QtCore import SignalInstance

from fit_acquisition.tasks.task_worker import TaskWorker



def _iter_worker_classes():
    import fit_acquisition.tasks as tasks_pkg

    prefix = tasks_pkg.__name__ + "."
    for module_info in pkgutil.walk_packages(tasks_pkg.__path__, prefix):
        module = importlib.import_module(module_info.name)
        for _, cls in inspect.getmembers(module, inspect.isclass):
            if not issubclass(cls, TaskWorker) or cls is TaskWorker:
                continue
            if cls.__module__ != module.__name__:
                continue
            yield cls


@pytest.mark.contract
def test_all_workers_expose_required_signals_and_methods() -> None:
    classes = list(_iter_worker_classes())

    assert classes, "No TaskWorker subclasses discovered"

    for cls in classes:
        worker = cls()
        assert isinstance(worker.started, SignalInstance)
        assert isinstance(worker.finished, SignalInstance)
        assert isinstance(worker.error, SignalInstance)
        assert callable(getattr(worker, "start", None))
        assert callable(getattr(worker, "stop", None))
        assert isinstance(worker.translations, dict)
