from __future__ import annotations

from collections import defaultdict
from types import SimpleNamespace

import pytest
from fit_common.gui.utils import State

from fit_acquisition import acquisition as acquisition_module
from fit_acquisition.class_names import class_names


class _SignalStub:
    def connect(self, _callback) -> None:
        return None


class _EmittingSignal:
    def __init__(self) -> None:
        self.callbacks = []

    def connect(self, callback) -> None:
        self.callbacks.append(callback)

    def emit(self) -> None:
        for callback in list(self.callbacks):
            callback()


class _PostAcquisitionStub:
    def __init__(self) -> None:
        self.finished = _SignalStub()


class _TasksManagerStub:
    def register_task_package(self, _package_name: str) -> None:
        return None

    def load_all_task_modules(self) -> None:
        return None

    def get_tasks(self) -> list:
        return []

    def clear_tasks(self) -> None:
        return None


class _StartTask:
    def __init__(self, state=State.INITIALIZATED) -> None:
        self.state = state
        self.started = _EmittingSignal()
        self.finished = _EmittingSignal()
        self.options = None
        self.increment = 0

    def start(self) -> None:
        return None

    def deleteLater(self) -> None:
        return None


class _StartTasksManager(_TasksManagerStub):
    def __init__(self, tasks) -> None:
        self.tasks = tasks

    def get_tasks(self) -> list:
        return self.tasks

    def get_tasks_from_class_name(self, _names) -> list:
        return self.tasks


@pytest.mark.unit
def test_remove_disable_tasks_filters_disabled_network_tools(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        acquisition_module, "load_translations", lambda: defaultdict(str)
    )
    monkeypatch.setattr(acquisition_module, "TasksManager", _TasksManagerStub)
    monkeypatch.setattr(acquisition_module, "PostAcquisition", _PostAcquisitionStub)
    monkeypatch.setattr(
        acquisition_module,
        "NetworkToolController",
        lambda: SimpleNamespace(
            configuration={
                "ssl_keylog": False,
                "ssl_certificate": True,
                "headers": False,
                "whois": True,
                "nslookup": False,
                "traceroute": True,
            }
        ),
    )
    monkeypatch.setattr(
        acquisition_module,
        "PacketCaptureController",
        lambda: SimpleNamespace(configuration={"enabled": True}),
    )
    monkeypatch.setattr(
        acquisition_module,
        "ScreenRecorderController",
        lambda: SimpleNamespace(configuration={"enabled_video": True}),
    )
    monkeypatch.setattr(
        acquisition_module,
        "TimestampController",
        lambda: SimpleNamespace(configuration={"enabled": True}),
    )
    monkeypatch.setattr(
        acquisition_module,
        "PecController",
        lambda: SimpleNamespace(configuration={"enabled": True}),
    )

    acquisition = acquisition_module.Acquisition(logger=SimpleNamespace(name="test"))
    filtered = acquisition._Acquisition__remove_disable_tasks(
        [
            class_names.SSLKEYLOG,
            class_names.SSLCERTIFICATE,
            class_names.HEADERS,
            class_names.WHOIS,
            class_names.NSLOOKUP,
            class_names.TRACEROUTE,
        ]
    )

    assert class_names.SSLKEYLOG not in filtered
    assert class_names.HEADERS not in filtered
    assert class_names.NSLOOKUP not in filtered
    assert class_names.SSLCERTIFICATE in filtered
    assert class_names.WHOIS in filtered
    assert class_names.TRACEROUTE in filtered


@pytest.mark.unit
@pytest.mark.parametrize(
    "states",
    [
        (State.STARTED, State.STARTED),
        (State.STARTED, State.COMPLETED),
        (State.COMPLETED, State.COMPLETED),
    ],
)
def test_start_phase_finishes_when_every_task_has_settled(
    monkeypatch: pytest.MonkeyPatch, states
) -> None:
    tasks = [_StartTask(state) for state in states]
    acquisition = _make_start_acquisition(monkeypatch, tasks)
    emissions = []
    acquisition.start_tasks_finished.connect(lambda: emissions.append(True))

    acquisition.run_start_tasks()
    tasks[0].started.emit()
    tasks[1].finished.emit()
    tasks[1].finished.emit()

    assert emissions == [True]


@pytest.mark.unit
def test_start_phase_waits_while_any_task_is_unsettled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tasks = [_StartTask(State.STARTED), _StartTask(State.INITIALIZATED)]
    acquisition = _make_start_acquisition(monkeypatch, tasks)
    emissions = []
    acquisition.start_tasks_finished.connect(lambda: emissions.append(True))

    acquisition.run_start_tasks()
    tasks[0].started.emit()

    assert emissions == []


def _make_start_acquisition(monkeypatch, tasks):
    manager = _StartTasksManager(tasks)
    monkeypatch.setattr(acquisition_module, "load_translations", lambda: defaultdict(str))
    monkeypatch.setattr(acquisition_module, "TasksManager", lambda: manager)
    monkeypatch.setattr(acquisition_module, "PostAcquisition", _PostAcquisitionStub)
    acquisition = acquisition_module.Acquisition(logger=SimpleNamespace(name="test"))
    acquisition.start_tasks = ["Task" for _ in tasks]
    acquisition.options = {"acquisition_directory": "/tmp"}
    return acquisition
