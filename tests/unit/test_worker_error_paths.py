from __future__ import annotations

import builtins

import pytest
from PySide6 import QtWidgets

from fit_acquisition.tasks.infinite_loop import screen_recorder as screen_module
from fit_acquisition.tasks.network_tools import headers as headers_module
from fit_acquisition.tasks.network_tools import nslookup as nslookup_module
from fit_acquisition.tasks.network_tools import whois as whois_module


@pytest.mark.unit
@pytest.mark.parametrize(
    ("worker_cls", "options"),
    [
        (headers_module.HeadersWorker, {"url": "not-a-url"}),
        (
            nslookup_module.NslookupWorker,
            {
                "url": "not-a-url",
                "nslookup_dns_server": "1.1.1.1",
                "nslookup_enable_verbose_mode": False,
                "nslookup_enable_tcp": False,
            },
        ),
        (whois_module.WhoisWorker, {"url": "###"}),
    ],
)
def test_workers_emit_error_payload_on_invalid_input(worker_cls, options) -> None:
    worker = worker_cls()
    worker.options = options

    errors: list[dict] = []
    worker.error.connect(lambda payload: errors.append(payload))

    worker.start()

    assert len(errors) == 1
    payload = errors[0]
    assert {"title", "message", "details"}.issubset(payload)
    assert isinstance(payload["message"], str)
    assert isinstance(payload["details"], str)


@pytest.mark.unit
def test_screen_recorder_emits_error_when_moviepy_missing(
    qapp: QtWidgets.QApplication, monkeypatch: pytest.MonkeyPatch
) -> None:
    worker = screen_module.ScreenRecorderWorker()

    # Force merge path without touching real media files.
    worker._ScreenRecorderWorker__is_enabled_audio_recording = True
    worker._ScreenRecorderWorker__audio_path = "/tmp/audio"
    worker._ScreenRecorderWorker__video_path = "/tmp/video"
    worker._ScreenRecorderWorker__filename = "/tmp/out"
    monkeypatch.setattr(
        worker,
        "_ScreenRecorderWorker__get_file_path",
        lambda _path: "/tmp/fake.bin",
    )

    original_import = builtins.__import__

    def _fake_import(name, *args, **kwargs):
        if name == "moviepy":
            raise ImportError("moviepy not installed")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", _fake_import)

    errors: list[dict] = []
    worker.error.connect(lambda payload: errors.append(payload))

    worker._ScreenRecorderWorker__join_audio_and_video()

    assert len(errors) == 1
    payload = errors[0]
    assert payload["details"]
    assert "moviepy" in payload["details"].lower()
