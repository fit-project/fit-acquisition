from __future__ import annotations

import subprocess
import threading
from pathlib import Path
from types import SimpleNamespace

import pytest
from PySide6.QtCore import Qt

from fit_acquisition.privileged import authorization as authorization_module
from fit_acquisition.privileged import runner as runner_module
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

    class Process:
        returncode = 0
        pid = 123
        def communicate(self, timeout=None):
            return b"ok", b""
        def poll(self):
            return 0

    monkeypatch.setattr(runner_module.subprocess, "Popen", lambda argv, **kwargs: (calls.append((argv, kwargs)) or Process()))
    runner = PrivilegedRunner()
    runner.start("traceroute", ["example.org"])
    assert runner.wait() == b"ok"
    assert calls[0][0][:2] == ["/usr/bin/sudo", "-A"]
    assert calls[0][1]["shell"] is False


@pytest.mark.unit
def test_runner_failure_and_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    failed = SimpleNamespace(returncode=2, communicate=lambda timeout=None: (b"", b"crash"))
    runner = PrivilegedRunner()
    runner._process = failed
    with pytest.raises(PrivilegedProcessError, match="crash"):
        runner.wait()

    class TimedOut:
        pid = 123
        returncode = None
        calls = 0
        def communicate(self, timeout=None):
            self.calls += 1
            if self.calls == 1:
                raise subprocess.TimeoutExpired("cmd", timeout)
            return b"", b""
        def poll(self):
            return None

    timed = TimedOut()
    runner._process = timed
    monkeypatch.setattr(runner, "cancel", lambda: None)
    with pytest.raises(PrivilegedProcessError) as exc:
        runner.wait(timeout=1)
    assert exc.value.code == "timeout"


class _Approved:
    def __init__(self):
        self.operations = []
    def require(self, operation):
        self.operations.append(operation)


@pytest.mark.unit
def test_linux_packet_capture_requests_and_stops(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(packet_module.sys, "platform", "linux")
    runner = SimpleNamespace(start=lambda action, args: None, cancel=lambda: None, wait=lambda timeout: b"pcap")
    monkeypatch.setattr(packet_module, "PrivilegedRunner", lambda: runner)
    worker = packet_module.PacketCaptureWorker()
    auth = _Approved()
    worker.privilege_authorization = auth
    worker.options = {"acquisition_directory": str(tmp_path), "filename": "capture.pcap"}
    worker.start()
    worker.stop()
    assert auth.operations == ["packet_capture"]
    assert (tmp_path / "capture.pcap").read_bytes() == b"pcap"


@pytest.mark.unit
def test_linux_traceroute_requests_and_writes_user_file(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(traceroute_module.sys, "platform", "linux")
    payload = b'[{"ttl": 2, "ip": "1.2.3.4", "tcp_response": true}]'
    runner = SimpleNamespace(start=lambda action, args: None, wait=lambda timeout: payload, cancel=lambda: None)
    monkeypatch.setattr(traceroute_module, "PrivilegedRunner", lambda: runner)
    worker = traceroute_module.TracerouteWorker()
    auth = _Approved()
    worker.privilege_authorization = auth
    worker.options = {"url": "https://example.org", "acquisition_directory": str(tmp_path)}
    worker.start()
    assert auth.operations == ["traceroute"]
    assert (tmp_path / "traceroute.txt").read_text() == "TTL=2 IP=1.2.3.4 TCP_response=True\n"
