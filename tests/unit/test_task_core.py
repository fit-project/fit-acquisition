from __future__ import annotations

from types import SimpleNamespace

import pytest
from fit_common.gui.utils import State, Status

from fit_acquisition.tasks.task import Task
from fit_acquisition.tasks.task_worker import TaskWorker
from fit_acquisition.tasks.tasks_handler import TasksHandler


class _Logger:
    def __init__(self) -> None:
        self.messages: list[str] = []

    def info(self, message: str) -> None:
        self.messages.append(message)


@pytest.mark.unit
def test_taskworker_options_roundtrip() -> None:
    worker = TaskWorker()
    worker.options = {"k": "v"}

    assert worker.options == {"k": "v"}
    assert isinstance(worker.translations, dict)


@pytest.mark.unit
def test_task_start_and_stop_delegate_without_ui() -> None:
    task = Task(_Logger(), None, None, label="HEADERS")
    task.options = {"url": "https://example.org"}

    calls = {"thread_start": 0, "worker_stop": 0}

    task.worker = SimpleNamespace(
        options=None,
        stop=lambda: calls.__setitem__("worker_stop", calls["worker_stop"] + 1),
    )
    task.worker_thread = SimpleNamespace(
        start=lambda: calls.__setitem__("thread_start", calls["thread_start"] + 1)
    )

    task.start_task("start-msg")
    task.stop_task("stop-msg")

    assert task.state == State.STOPPED
    assert task.status == Status.PENDING
    assert task.worker.options == {"url": "https://example.org"}
    assert calls["thread_start"] == 1
    assert calls["worker_stop"] == 1


@pytest.mark.unit
def test_task_handle_error_sets_failure_details() -> None:
    logger = _Logger()
    task = Task(logger, None, None, label="HEADERS")

    task._handle_error({"details": "boom"})

    assert task.state == State.COMPLETED
    assert task.status == Status.FAILURE
    assert task.details == "boom"


@pytest.mark.unit
def test_tasks_handler_singleton_and_state_match() -> None:
    handler1 = TasksHandler()
    handler2 = TasksHandler()

    handler1.clear_tasks()
    handler1.add_task(SimpleNamespace(__class__=SimpleNamespace(__name__="TaskA"), state=State.COMPLETED))

    # SimpleNamespace doesn't let us set __class__.__name__ reliably for get_task.
    class _TaskA:
        state = State.COMPLETED

    class _TaskB:
        state = State.COMPLETED

    t1 = _TaskA()
    t2 = _TaskB()
    handler1.clear_tasks()
    handler1.add_task(t1)
    handler1.add_task(t2)

    assert handler1 is handler2
    assert handler1.get_task("_TaskA") is t1
    assert handler1.are_task_names_in_the_same_state(["_TaskA", "_TaskB"], State.COMPLETED) is True
