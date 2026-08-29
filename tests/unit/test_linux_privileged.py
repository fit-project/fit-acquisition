from __future__ import annotations

import subprocess
import sys
import threading
import time
from pathlib import Path
from types import SimpleNamespace

import pytest
from PySide6.QtCore import Qt

from fit_acquisition.privileged import authorization as authorization_module
from fit_acquisition.privileged import packet_capture as privileged_packet_module
from fit_acquisition.privileged import runner as runner_module
from fit_acquisition.privileged import traceroute as privileged_traceroute_module
from fit_acquisition.privileged.authorization import PrivilegeAuthorization, PrivilegeDeniedError
from fit_acquisition.privileged.runner import PrivilegedProcessError, PrivilegedRunner
from fit_acquisition.tasks.infinite_loop import packet_capture as packet_module
from fit_acquisition.tasks.network_tools import traceroute as traceroute_module


@pytest.mark.unit
def test_no_request_outside_linux(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(authorization_module.sys, "platform", "darwin")
    authorization = PrivilegeAuthorization()
    requests = []
    authorization.requested.connect(requests.append, Qt.ConnectionType.DirectConnection)
    authorization.require("traceroute")
    assert requests == []


@pytest.mark.unit
def test_approval_is_shared_by_concurrent_tasks(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(authorization_module.sys, "platform", "linux")
    authorization = PrivilegeAuthorization()
    requests = []
    authorization.requested.connect(requests.append, Qt.ConnectionType.DirectConnection)
    results = []
    threads = [threading.Thread(target=lambda op=op: (authorization.require(op), results.append(op))) for op in ("packet_capture", "traceroute")]
    for thread in threads:
        thread.start()
    while not requests:
        threading.Event().wait(0.01)
    assert authorization.respond(requests[0]["request_id"], True) is True
    assert authorization.respond(requests[0]["request_id"], True) is False
    for thread in threads:
        thread.join(timeout=1)
    assert len(requests) == 1
    assert sorted(results) == ["packet_capture", "traceroute"]


@pytest.mark.unit
def test_rejection_is_explicit(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(authorization_module.sys, "platform", "linux")
    authorization = PrivilegeAuthorization()
    requests = []
    authorization.requested.connect(requests.append, Qt.ConnectionType.DirectConnection)
    errors = []
    thread = threading.Thread(target=lambda: _capture_error(authorization, errors))
    thread.start()
    while not requests:
        threading.Event().wait(0.01)
    authorization.respond(requests[0]["request_id"], False)
    thread.join(timeout=1)
    assert isinstance(errors[0], PrivilegeDeniedError)


@pytest.mark.unit
def test_authorization_reset_requires_a_new_confirmation(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(authorization_module.sys, "platform", "linux")
    authorization = PrivilegeAuthorization()
    requests = []
    authorization.requested.connect(requests.append, Qt.ConnectionType.DirectConnection)

    first = threading.Thread(target=lambda: authorization.require("traceroute"))
    first.start()
    while len(requests) < 1:
        threading.Event().wait(0.01)
    authorization.respond(requests[0]["request_id"], True)
    first.join(timeout=1)

    authorization.reset()
    second = threading.Thread(target=lambda: authorization.require("traceroute"))
    second.start()
    while len(requests) < 2:
        threading.Event().wait(0.01)
    authorization.respond(requests[1]["request_id"], True)
    second.join(timeout=1)

    assert requests[0]["request_id"] != requests[1]["request_id"]


def _capture_error(authorization: PrivilegeAuthorization, errors: list[Exception]) -> None:
    try:
        authorization.require("packet_capture")
    except Exception as error:
        errors.append(error)


@pytest.mark.unit
def test_missing_askpass(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("FIT_LINUX_SUDO_ASKPASS", raising=False)
    with pytest.raises(PrivilegedProcessError, match="FIT_LINUX_SUDO_ASKPASS") as exc:
        PrivilegedRunner._environment()
    assert exc.value.code == "askpass_missing"


@pytest.mark.unit
def test_missing_sudo(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(runner_module.sys, "platform", "linux")
    monkeypatch.setattr(runner_module.shutil, "which", lambda _: None)
    with pytest.raises(PrivilegedProcessError) as exc:
        PrivilegedRunner.command("traceroute", ["example.org"])
    assert exc.value.code == "sudo_missing"


@pytest.mark.unit
def test_runner_uses_argv_and_never_shell(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    askpass = tmp_path / "askpass"
    askpass.write_text("helper")
    monkeypatch.setenv("FIT_LINUX_SUDO_ASKPASS", str(askpass))
    monkeypatch.setattr(runner_module.sys, "platform", "linux")
    monkeypatch.setattr(runner_module.shutil, "which", lambda _: "/usr/bin/sudo")
    calls = []

    original_popen = subprocess.Popen

    def popen(argv, **kwargs):
        calls.append((argv, kwargs))
        return original_popen(
            [
                sys.executable,
                "-c",
                "import sys; "
                "sys.stderr.write('diagnostic\\nFIT_PRIVILEGED_READY\\n'); "
                "sys.stderr.flush(); sys.stdout.buffer.write(b'ok')",
            ],
            **kwargs,
        )

    monkeypatch.setattr(runner_module.subprocess, "Popen", popen)
    runner = PrivilegedRunner()
    runner.start("traceroute", ["example.org"])
    assert runner.wait() == b"ok"
    assert calls[0][0][:2] == ["/usr/bin/sudo", "-A"]
    assert calls[0][1]["shell"] is False
    assert calls[0][1]["start_new_session"] is True
    assert runner._diagnostics() == "diagnostic"


@pytest.mark.unit
def test_runner_process_exit_before_ready_preserves_stderr(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _mock_privileged_process(
        monkeypatch,
        tmp_path,
        "import sys; sys.stderr.write('sudo: authentication failed\\n'); sys.exit(1)",
    )
    with pytest.raises(PrivilegedProcessError, match="authentication failed") as exc:
        PrivilegedRunner().start("traceroute", ["example.org"])
    assert exc.value.code == "authentication_cancelled"


@pytest.mark.unit
def test_runner_clean_exit_without_ready_is_failure(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _mock_privileged_process(monkeypatch, tmp_path, "pass")
    with pytest.raises(PrivilegedProcessError) as exc:
        PrivilegedRunner().start("traceroute", ["example.org"])
    assert exc.value.code == "readiness_missing"


@pytest.mark.unit
def test_runner_readiness_timeout_cleans_process_group(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _mock_privileged_process(monkeypatch, tmp_path, "import time; time.sleep(60)")
    original_killpg = runner_module.os.killpg
    signals = []

    def killpg(pid, sig):
        signals.append(sig)
        original_killpg(pid, sig)

    monkeypatch.setattr(runner_module.os, "killpg", killpg)
    runner = PrivilegedRunner()
    with pytest.raises(PrivilegedProcessError) as exc:
        runner.start("traceroute", ["example.org"], readiness_timeout=0.05)
    assert exc.value.code == "readiness_timeout"
    assert runner_module.signal.SIGTERM in signals
    assert runner.active is False


@pytest.mark.unit
def test_runner_cancel_interrupts_readiness_and_is_idempotent(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _mock_privileged_process(monkeypatch, tmp_path, "import time; time.sleep(60)")
    runner = PrivilegedRunner()
    errors = []
    thread = threading.Thread(
        target=lambda: _capture_runner_start_error(runner, errors)
    )
    thread.start()
    deadline = time.monotonic() + 2
    while not runner.active and time.monotonic() < deadline:
        threading.Event().wait(0.01)
    runner.cancel()
    runner.cancel()
    thread.join(timeout=2)
    assert not thread.is_alive()
    assert errors and errors[0].code == "process_failed"
    assert runner.active is False


@pytest.mark.unit
def test_runner_wait_timeout_cleans_ready_process(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _mock_privileged_process(
        monkeypatch,
        tmp_path,
        "import sys, time; sys.stderr.write('FIT_PRIVILEGED_READY\\n'); "
        "sys.stderr.flush(); time.sleep(60)",
    )
    runner = PrivilegedRunner()
    runner.start("traceroute", ["example.org"])
    with pytest.raises(PrivilegedProcessError) as exc:
        runner.wait(timeout=0.05)
    assert exc.value.code == "timeout"
    assert runner.active is False


def _capture_runner_start_error(
    runner: PrivilegedRunner, errors: list[PrivilegedProcessError]
) -> None:
    try:
        runner.start("traceroute", ["example.org"])
    except PrivilegedProcessError as error:
        errors.append(error)


def _mock_privileged_process(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, script: str
) -> None:
    askpass = tmp_path / "askpass"
    askpass.write_text("helper")
    monkeypatch.setenv("FIT_LINUX_SUDO_ASKPASS", str(askpass))
    monkeypatch.setattr(runner_module.sys, "platform", "linux")
    monkeypatch.setattr(runner_module.shutil, "which", lambda _: "/usr/bin/sudo")
    original_popen = subprocess.Popen
    monkeypatch.setattr(
        runner_module.subprocess,
        "Popen",
        lambda _argv, **kwargs: original_popen(
            [sys.executable, "-c", script], **kwargs
        ),
    )


@pytest.mark.unit
def test_privileged_packet_capture_reports_ready_after_sniffer_start(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    events = []

    class Sniffer:
        results = []
        def start(self):
            events.append("sniffer-started")
        def stop(self):
            events.append("sniffer-stopped")

    class ImmediateEvent:
        def set(self):
            return None
        def wait(self):
            return None

    monkeypatch.setattr(privileged_packet_module.scapy, "AsyncSniffer", Sniffer)
    monkeypatch.setattr(privileged_packet_module.scapy, "wrpcap", lambda *_: None)
    monkeypatch.setattr(privileged_packet_module.threading, "Event", ImmediateEvent)
    monkeypatch.setattr(privileged_packet_module.signal, "signal", lambda *_: None)

    privileged_packet_module.capture_to_stdout(lambda: events.append("ready"))

    assert events == ["sniffer-started", "ready", "sniffer-stopped"]


@pytest.mark.unit
def test_privileged_traceroute_opens_socket_before_ready(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    events = []

    class Socket:
        def sr(self, _packets, **kwargs):
            events.append("socket-sr")
            assert kwargs == {"timeout": 10, "verbose": False}
            return [], []

        def close(self):
            events.append("socket-closed")

    socket = Socket()
    monkeypatch.setattr(
        privileged_traceroute_module.scapy.conf,
        "L3socket",
        lambda: (events.append("socket-opened") or socket),
    )

    monkeypatch.setattr(
        privileged_traceroute_module.scapy,
        "sr",
        lambda *_args, **_kwargs: pytest.fail("scapy.sr must not be used"),
    )
    rows = privileged_traceroute_module.run_traceroute(
        "127.0.0.1", lambda: events.append("ready")
    )

    assert rows == []
    assert events == ["socket-opened", "ready", "socket-sr", "socket-closed"]


@pytest.mark.unit
def test_privileged_traceroute_closes_socket_when_sr_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    events = []

    class Socket:
        def sr(self, _packets, **_kwargs):
            events.append("socket-sr")
            raise RuntimeError("send failed")

        def close(self):
            events.append("socket-closed")

    monkeypatch.setattr(
        privileged_traceroute_module.scapy.conf, "L3socket", Socket
    )

    with pytest.raises(RuntimeError, match="send failed"):
        privileged_traceroute_module.run_traceroute(
            "127.0.0.1", lambda: events.append("ready")
        )

    assert events == ["ready", "socket-sr", "socket-closed"]


@pytest.mark.unit
def test_privileged_traceroute_does_not_report_ready_when_socket_open_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    events = []

    def fail_to_open():
        events.append("socket-open-failed")
        raise OSError("permission denied")

    monkeypatch.setattr(
        privileged_traceroute_module.scapy.conf, "L3socket", fail_to_open
    )

    with pytest.raises(OSError, match="permission denied"):
        privileged_traceroute_module.run_traceroute(
            "127.0.0.1", lambda: events.append("ready")
        )

    assert events == ["socket-open-failed"]


@pytest.mark.unit
def test_privileged_traceroute_converts_answers_to_json_rows(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class Socket:
        def sr(self, _packets, **_kwargs):
            return [
                (
                    SimpleNamespace(ttl=3),
                    SimpleNamespace(src="192.0.2.1", payload=scapy_tcp),
                ),
                (
                    SimpleNamespace(ttl=4),
                    SimpleNamespace(src="198.51.100.2", payload=object()),
                ),
            ], []

        def close(self):
            return None

    scapy_tcp = privileged_traceroute_module.scapy.TCP()
    monkeypatch.setattr(
        privileged_traceroute_module.scapy.conf, "L3socket", Socket
    )

    rows = privileged_traceroute_module.run_traceroute("example.org", lambda: None)

    assert rows == [
        {"ttl": 3, "ip": "192.0.2.1", "tcp_response": True},
        {"ttl": 4, "ip": "198.51.100.2", "tcp_response": False},
    ]


class _Approved:
    def __init__(self):
        self.operations = []
    def require(self, operation):
        self.operations.append(operation)


@pytest.mark.unit
def test_linux_packet_capture_requests_and_stops(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(packet_module.sys, "platform", "linux")
    events = []

    pcap = b"\xd4\xc3\xb2\xa1" + (b"\x00" * 20)

    class Runner:
        def start(self, action, args):
            assert events == []
            events.append("ready")
        def cancel(self):
            events.append("cancel")
        def wait(self, timeout):
            return pcap

    runner = Runner()
    monkeypatch.setattr(packet_module, "PrivilegedRunner", lambda: runner)
    worker = packet_module.PacketCaptureWorker()
    auth = _Approved()
    worker.privilege_authorization = auth
    worker.options = {"acquisition_directory": str(tmp_path), "filename": "capture.pcap"}
    worker.started.connect(lambda: events.append("started"))
    worker.start()
    worker.stop()
    assert events[:2] == ["ready", "started"]
    assert auth.operations == ["packet_capture"]
    assert (tmp_path / "capture.pcap").read_bytes() == pcap


@pytest.mark.unit
def test_linux_traceroute_requests_and_writes_user_file(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(traceroute_module.sys, "platform", "linux")
    payload = b'[{"ttl": 2, "ip": "1.2.3.4", "tcp_response": true}]'
    events = []

    class Runner:
        def start(self, action, args):
            assert events == []
            events.append("ready")
        def wait(self, timeout):
            return payload
        def cancel(self):
            events.append("cancel")

    runner = Runner()
    monkeypatch.setattr(traceroute_module, "PrivilegedRunner", lambda: runner)
    worker = traceroute_module.TracerouteWorker()
    auth = _Approved()
    worker.privilege_authorization = auth
    worker.options = {"url": "https://example.org", "acquisition_directory": str(tmp_path)}
    worker.started.connect(lambda: events.append("started"))
    worker.start()
    assert events[:2] == ["ready", "started"]
    assert auth.operations == ["traceroute"]
    assert (tmp_path / "traceroute.txt").read_text() == "TTL=2 IP=1.2.3.4 TCP_response=True\n"


@pytest.mark.unit
@pytest.mark.parametrize("worker_module, worker_class", [
    (packet_module, packet_module.PacketCaptureWorker),
    (traceroute_module, traceroute_module.TracerouteWorker),
])
def test_linux_worker_start_failure_never_emits_started(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    worker_module,
    worker_class,
) -> None:
    monkeypatch.setattr(worker_module.sys, "platform", "linux")

    class FailedRunner:
        def start(self, action, args):
            raise PrivilegedProcessError("process_failed", "sudo failed")
        def cancel(self):
            return None

    monkeypatch.setattr(worker_module, "PrivilegedRunner", FailedRunner)
    worker = worker_class()
    worker.privilege_authorization = _Approved()
    worker.options = (
        {"acquisition_directory": str(tmp_path), "filename": "capture.pcap"}
        if worker_module is packet_module
        else {"url": "https://example.org", "acquisition_directory": str(tmp_path)}
    )
    started = []
    errors = []
    worker.started.connect(lambda: started.append(True))
    worker.error.connect(errors.append)
    worker.start()
    assert started == []
    assert errors and "sudo failed" in errors[0]["details"]
    assert worker.privileged_runner is None
