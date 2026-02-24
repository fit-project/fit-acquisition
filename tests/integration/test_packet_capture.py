from __future__ import annotations

from types import SimpleNamespace

import pytest

from fit_acquisition.tasks.infinite_loop import packet_capture as packet_module


@pytest.mark.integration
def test_packet_capture_worker_start_and_stop(monkeypatch: pytest.MonkeyPatch) -> None:
    worker = packet_module.PacketCaptureWorker()
    worker.options = {
        "acquisition_directory": "/tmp/acq",
        "filename": "network.pcap",
        "output_file": "/tmp/acq/network.pcap",
    }

    calls: dict[str, int] = {"start": 0, "stop": 0, "wrpcap": 0}

    worker.sniffer = SimpleNamespace(
        results=["pkt"],
        start=lambda: calls.__setitem__("start", calls["start"] + 1),
        stop=lambda: calls.__setitem__("stop", calls["stop"] + 1),
    )

    monkeypatch.setattr(packet_module, "QEventLoop", lambda: SimpleNamespace(exec=lambda: None, quit=lambda: None))
    monkeypatch.setattr(packet_module.QTimer, "singleShot", lambda ms, fn: fn())
    monkeypatch.setattr(
        packet_module.scapy,
        "wrpcap",
        lambda path, data: calls.__setitem__("wrpcap", calls["wrpcap"] + 1),
    )

    events: list[str] = []
    worker.started.connect(lambda: events.append("started"))
    worker.finished.connect(lambda: events.append("finished"))

    worker.start()
    worker.stop()

    assert events == ["started", "finished"]
    assert calls == {"start": 1, "stop": 1, "wrpcap": 1}


@pytest.mark.integration
def test_task_packet_capture_options_uses_controller(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        packet_module,
        "PacketCaptureController",
        lambda: SimpleNamespace(configuration={"filename": "cap.pcap"}),
    )

    class _Logger:
        def info(self, message: str) -> None:
            return None

    task = packet_module.TaskPacketCapture(_Logger())
    task.options = {"acquisition_directory": "/tmp/acq"}

    assert task.options["acquisition_directory"] == "/tmp/acq"
    assert task.options["filename"] == "cap.pcap"
