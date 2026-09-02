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

    def init_tasks(self, *_args) -> None:
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


@pytest.mark.unit
def test_acquisition_shares_and_closes_one_linux_privileged_session(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    sessions = []

    class Session:
        def __init__(self, directory=None):
            self.directory = directory
            self.closed = 0
            self.started = False
            sessions.append(self)

        def close(self):
            self.closed = 1

    class TaskStub:
        privilege_authorization = None
        privileged_session = None

        def deleteLater(self):
            return None

    task_one = TaskStub()
    task_two = TaskStub()
    manager = _StartTasksManager([task_one, task_two])
    monkeypatch.setattr(acquisition_module.sys, "platform", "linux")
    monkeypatch.setattr(acquisition_module, "PrivilegedSession", Session)
    monkeypatch.setattr(acquisition_module, "load_translations", lambda: defaultdict(str))
    monkeypatch.setattr(acquisition_module, "TasksManager", lambda: manager)
    monkeypatch.setattr(acquisition_module, "PostAcquisition", _PostAcquisitionStub)
    monkeypatch.setattr(acquisition_module, "isValid", lambda _task: True)
    monkeypatch.setattr(
        acquisition_module,
        "LogConfigTools",
        lambda: SimpleNamespace(
            config={"version": 1},
            change_filehandlers_path=lambda _path: None,
        ),
    )

    acquisition = acquisition_module.Acquisition(logger=SimpleNamespace(name="test"))
    acquisition.options = {"acquisition_directory": str(tmp_path)}
    acquisition.load_tasks()

    assert task_one.privileged_session is task_two.privileged_session
    assert task_one.privileged_session is sessions[-1]
    assert sessions[-1].directory == str(tmp_path)
    assert sessions[-1].started is False

    acquisition.unload_tasks()
    acquisition.unload_tasks()
    assert sessions[-1].closed == 1


@pytest.mark.unit
def test_non_linux_acquisition_has_no_privileged_session(monkeypatch) -> None:
    monkeypatch.setattr(acquisition_module.sys, "platform", "darwin")
    monkeypatch.setattr(acquisition_module, "load_translations", lambda: defaultdict(str))
    monkeypatch.setattr(acquisition_module, "TasksManager", _TasksManagerStub)
    monkeypatch.setattr(acquisition_module, "PostAcquisition", _PostAcquisitionStub)

    acquisition = acquisition_module.Acquisition(logger=SimpleNamespace(name="test"))

    assert acquisition._privileged_session is None
