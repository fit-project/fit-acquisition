from __future__ import annotations

from types import SimpleNamespace

import pytest

from fit_acquisition.tasks.infinite_loop import screen_recorder as screen_module


class _Logger:
    def info(self, message: str) -> None:
        return None


@pytest.mark.integration
def test_task_screen_recorder_options_adds_filename(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        screen_module,
        "ScreenRecorderController",
        lambda: SimpleNamespace(configuration={"filename": "screenrecorder"}),
    )

    task = screen_module.TaskScreenRecorder(_Logger())
    task.options = {"acquisition_directory": "/tmp/acq"}

    assert task.options["filename"] == "/tmp/acq/screenrecorder"


@pytest.mark.integration
def test_task_screen_recorder_start_and_stop_delegate(monkeypatch: pytest.MonkeyPatch) -> None:
    task = screen_module.TaskScreenRecorder(_Logger())
    calls: list[tuple[str, str]] = []

    monkeypatch.setattr(screen_module.Task, "start_task", lambda self, msg: calls.append(("start", msg)))
    monkeypatch.setattr(screen_module.Task, "stop_task", lambda self, msg: calls.append(("stop", msg)))

    task.start()
    task.stop()

    assert calls == [
        ("start", task.translations["SCREEN_RECORDER_STARTED"]),
        ("stop", task.translations["SCREEN_RECORDER_STOPPED"]),
    ]
