from __future__ import annotations

import os

import pytest

from fit_acquisition.tasks.network_tools import sslkeylog as sslkeylog_module


@pytest.mark.integration
def test_sslkeylog_worker_sets_env_var() -> None:
    worker = sslkeylog_module.SSLKeyLogWorker()
    worker.options = {"acquisition_directory": "/tmp/acq"}

    events: list[str] = []
    worker.started.connect(lambda: events.append("started"))
    worker.finished.connect(lambda: events.append("finished"))

    worker.start()

    assert events == ["started", "finished"]
    assert os.environ["SSLKEYLOGFILE"].endswith("/tmp/acq/sslkey.log")
