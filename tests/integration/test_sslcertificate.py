from __future__ import annotations

import pytest

from fit_acquisition.tasks.network_tools import sslcertificate as ssl_module


@pytest.mark.integration
def test_sslcertificate_worker_saves_certificate(monkeypatch: pytest.MonkeyPatch) -> None:
    worker = ssl_module.SSLCertificateWorker()
    worker.options = {
        "url": "https://example.org",
        "acquisition_directory": "/tmp/fake",
    }

    saved: list[tuple[str, str]] = []

    monkeypatch.setattr(
        worker,
        "_SSLCertificateWorker__check_if_peer_certificate_exist",
        lambda url: True,
    )
    monkeypatch.setattr(
        worker,
        "_SSLCertificateWorker__get_peer_PEM_cert",
        lambda url: "PEM-CONTENT",
    )
    monkeypatch.setattr(
        worker,
        "_SSLCertificateWorker__save_PEM_cert_to_CER_cert",
        lambda path, cert: saved.append((path, cert)),
    )

    events: list[str] = []
    worker.started.connect(lambda: events.append("started"))
    worker.finished.connect(lambda: events.append("finished"))

    worker.start()

    assert events == ["started", "finished"]
    assert saved == [("/tmp/fake/server.cer", "PEM-CONTENT")]
