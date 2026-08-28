from __future__ import annotations

from collections import defaultdict
from types import SimpleNamespace

import pytest

from fit_acquisition import acquisition as acquisition_module


class _Signal:
    def connect(self, _callback):
        return None


class _Manager:
    def register_task_package(self, _package):
        return None

    def load_all_task_modules(self):
        return None

    def get_tasks(self):
        return []

    def clear_tasks(self):
        return None


@pytest.mark.contract
def test_acquisition_exposes_privilege_response_api(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(acquisition_module, "TasksManager", _Manager)
    monkeypatch.setattr(acquisition_module, "load_translations", lambda: defaultdict(str))
    monkeypatch.setattr(acquisition_module, "PostAcquisition", lambda: SimpleNamespace(finished=_Signal()))
    acquisition = acquisition_module.Acquisition(SimpleNamespace(name="test"))

    assert hasattr(acquisition, "privilege_requested")
    assert callable(acquisition.respond_to_privilege_request)
    assert callable(acquisition.approve_privilege_request)
    assert callable(acquisition.reject_privilege_request)
