from __future__ import annotations

import io
import json
import threading
from pathlib import Path
from types import SimpleNamespace

import pytest

from fit_acquisition.privileged import broker as broker_module
from fit_acquisition.privileged import session as session_module
from fit_acquisition.privileged.runner import PrivilegedProcessError


class _AliveProcess:
    stdin = io.BytesIO()
    stdout = io.BytesIO()
    stderr = io.BytesIO()
    pid = 1234
    returncode = None

    def poll(self):
        return self.returncode


@pytest.mark.unit
def test_session_starts_one_broker_for_multiple_starts(
    monkeypatch, tmp_path: Path
) -> None:
    askpass = tmp_path / "askpass"
    askpass.write_text("helper")
    monkeypatch.setenv("FIT_LINUX_SUDO_ASKPASS", str(askpass))
    monkeypatch.setattr(session_module.sys, "platform", "linux")
    monkeypatch.setattr(session_module.shutil, "which", lambda _name: "/usr/bin/sudo")
    process = _AliveProcess()
    popen_calls = []

    def popen(command, **kwargs):
        popen_calls.append((command, kwargs))
        return process

    monkeypatch.setattr(session_module.subprocess, "Popen", popen)
    session = session_module.PrivilegedSession(str(tmp_path))
    monkeypatch.setattr(
        session,
        "_read_stdout",
        lambda _process: session._dispatch(
            {"request_id": None, "status": "session_ready"}
        ),
    )
    monkeypatch.setattr(session, "_read_stderr", lambda _process: None)
    monkeypatch.setattr(session, "_watch", lambda *_args: None)

    session.start(timeout=0.1)
    session.start(timeout=0.1)

    assert len(popen_calls) == 1
    command, kwargs = popen_calls[0]
    assert command[:2] == ["/usr/bin/sudo", "-A"]
    assert command[-2:] == ["broker", str(tmp_path.resolve())]
    assert kwargs["shell"] is False
    assert kwargs["start_new_session"] is True


@pytest.mark.unit
def test_session_is_lazy_and_reuses_ready_process(monkeypatch, tmp_path: Path) -> None:
    process = _AliveProcess()
    session = session_module.PrivilegedSession(str(tmp_path))
    assert session._process is None

    session._process = process
    session._session_ready = True
    starts = []
    monkeypatch.setattr(session, "start", lambda: starts.append(True))

    def send(message):
        session._dispatch(
            {
                "request_id": message["request_id"],
                "status": "completed",
                "result": [] if message["operation"] == "traceroute" else {},
            }
        )

    monkeypatch.setattr(session, "_send", send)
    session.request("traceroute", {"destination": "example.org"})
    session.request("stop_packet_capture", {"output_path": str(tmp_path / "x.pcap")})

    assert starts == [True, True]
    assert session._process is process


@pytest.mark.unit
def test_session_ready_unknown_id_and_duplicate_response() -> None:
    session = session_module.PrivilegedSession("/tmp/acq")
    session._dispatch({"request_id": None, "status": "session_ready"})
    assert session._session_ready is True

    session._dispatch({"request_id": "missing", "status": "completed", "result": {}})
    assert session._failure is not None
    assert session._failure.code == "protocol_error"

    duplicate = session_module.PrivilegedSession("/tmp/acq")
    pending = session_module._PendingRequest()
    duplicate._pending["id"] = pending
    duplicate._dispatch({"request_id": "id", "status": "completed", "result": {}})
    duplicate._dispatch({"request_id": "id", "status": "completed", "result": {}})
    assert duplicate._failure is not None
    assert duplicate._failure.code == "protocol_error"


@pytest.mark.unit
def test_session_timeout_is_isolated_and_late_responses_are_ignored(
    monkeypatch,
) -> None:
    process = _AliveProcess()
    session = session_module.PrivilegedSession("/tmp/acq")
    session._process = process
    session._session_ready = True
    monkeypatch.setattr(session, "start", lambda: None)
    request_ids = iter(("expired", "next"))
    monkeypatch.setattr(
        session_module.uuid,
        "uuid4",
        lambda: SimpleNamespace(hex=next(request_ids)),
    )

    def send(message):
        if message["request_id"] == "next":
            session._dispatch(
                {"request_id": "next", "status": "completed", "result": {}}
            )

    monkeypatch.setattr(session, "_send", send)

    with pytest.raises(PrivilegedProcessError) as exc:
        session.request(
            "stop_packet_capture", {"output_path": "/tmp/acq/x"}, timeout=0.01
        )

    assert exc.value.code == "timeout"
    assert session.active
    session._dispatch({"request_id": "expired", "status": "ready"})
    session._dispatch({"request_id": "expired", "status": "completed", "result": []})
    assert session._failure is None
    assert "expired" not in session._expired
    assert session.request("stop_packet_capture", {"output_path": "/tmp/acq/x"}) == {}


@pytest.mark.unit
def test_broker_processes_capture_stop_while_traceroute_is_blocked(
    monkeypatch, tmp_path: Path
) -> None:
    output = tmp_path / "capture.pcap"
    entered = threading.Event()
    release = threading.Event()
    stdout = io.StringIO()

    class Sniffer:
        def __init__(self):
            self.results = ["packet"]

        def start(self):
            return None

        def stop(self):
            return None

    monkeypatch.setattr(broker_module.scapy, "AsyncSniffer", Sniffer)

    def blocked_traceroute(_destination, ready):
        ready()
        entered.set()
        assert release.wait(1)
        return []

    monkeypatch.setattr(broker_module, "run_traceroute", blocked_traceroute)
    monkeypatch.setattr(
        broker_module.PrivilegedBroker,
        "_write_pcap",
        lambda _self, path, _packets: path.write_bytes(b"pcap"),
    )
    broker = broker_module.PrivilegedBroker(str(tmp_path), io.StringIO(), stdout)

    broker._handle("start", "start_packet_capture", {"output_path": str(output)})
    broker._handle("trace", "traceroute", {"destination": "example.org"})
    assert entered.wait(0.2)
    broker._handle("stop", "stop_packet_capture", {"output_path": str(output)})
    messages = [json.loads(line) for line in stdout.getvalue().splitlines()]
    assert any(
        m["request_id"] == "stop" and m["status"] == "completed" for m in messages
    )
    assert not any(
        m["request_id"] == "trace" and m["status"] == "completed"
        for m in messages
    )
    release.set()
    broker._executor.shutdown(wait=True)
    messages = [json.loads(line) for line in stdout.getvalue().splitlines()]
    assert any(
        m["request_id"] == "trace" and m["status"] == "completed"
        for m in messages
    )


@pytest.mark.unit
def test_broker_keeps_concurrent_traceroute_ids_and_survives_error(
    monkeypatch, tmp_path: Path
) -> None:
    releases = {"one": threading.Event(), "two": threading.Event()}
    entered = {"one": threading.Event(), "two": threading.Event()}
    stdout = io.StringIO()

    def traceroute(destination, ready):
        ready()
        entered[destination].set()
        assert releases[destination].wait(1)
        if destination == "one":
            raise RuntimeError("trace failed")
        return [{"ttl": 1, "ip": "192.0.2.2", "tcp_response": False}]

    monkeypatch.setattr(broker_module, "run_traceroute", traceroute)
    monkeypatch.setattr(
        broker_module.scapy,
        "AsyncSniffer",
        lambda: SimpleNamespace(start=lambda: None),
    )
    broker = broker_module.PrivilegedBroker(str(tmp_path), io.StringIO(), stdout)
    broker._handle("id-one", "traceroute", {"destination": "one"})
    broker._handle("id-two", "traceroute", {"destination": "two"})
    assert entered["one"].wait(0.2) and entered["two"].wait(0.2)
    releases["two"].set()
    releases["one"].set()
    broker._executor.shutdown(wait=True)

    messages = [json.loads(line) for line in stdout.getvalue().splitlines()]
    terminal = [message for message in messages if message["status"] != "ready"]
    assert {(m["request_id"], m["status"]) for m in terminal} == {
        ("id-two", "completed"),
        ("id-one", "error"),
    }
    assert broker._handle(
        "capture",
        "start_packet_capture",
        {"output_path": str(tmp_path / "capture.pcap")},
    )


@pytest.mark.unit
def test_broker_send_serializes_concurrent_json_lines(tmp_path: Path) -> None:
    stdout = io.StringIO()
    broker = broker_module.PrivilegedBroker(str(tmp_path), io.StringIO(), stdout)
    barrier = threading.Barrier(9)

    def send(index):
        barrier.wait()
        broker._send(str(index), "completed", result={"value": index})

    threads = [threading.Thread(target=send, args=(index,)) for index in range(8)]
    for thread in threads:
        thread.start()
    barrier.wait()
    for thread in threads:
        thread.join()
    broker._executor.shutdown(wait=True)

    messages = [json.loads(line) for line in stdout.getvalue().splitlines()]
    assert {message["request_id"] for message in messages} == {str(i) for i in range(8)}


@pytest.mark.unit
def test_broker_shutdown_is_bounded_and_suppresses_late_worker_output(
    monkeypatch, tmp_path: Path
) -> None:
    entered = threading.Event()
    release = threading.Event()
    stdout = io.StringIO()

    def traceroute(_destination, ready):
        ready()
        entered.set()
        assert release.wait(1)
        return []

    monkeypatch.setattr(broker_module, "run_traceroute", traceroute)
    monkeypatch.setattr(broker_module, "_SHUTDOWN_WAIT", 0.01)
    broker = broker_module.PrivilegedBroker(str(tmp_path), io.StringIO(), stdout)
    broker._handle("trace", "traceroute", {"destination": "example.org"})
    assert entered.wait(0.2)

    broker._shutdown("shutdown")
    messages_at_shutdown = stdout.getvalue()
    assert json.loads(messages_at_shutdown.splitlines()[-1]) == {
        "request_id": "shutdown",
        "status": "completed",
        "result": {},
    }
    release.set()
    broker._executor.shutdown(wait=True)
    assert stdout.getvalue() == messages_at_shutdown


@pytest.mark.unit
def test_session_malformed_message_and_eof_fail_pending_request() -> None:
    session = session_module.PrivilegedSession("/tmp/acq")
    pending = session_module._PendingRequest()
    session._pending["id"] = pending
    process = SimpleNamespace(stdout=io.BytesIO(b"not-json\n"))

    session._read_stdout(process)

    assert pending.error is not None
    assert pending.error.code == "protocol_error"


@pytest.mark.unit
def test_session_close_is_idempotent_and_unblocks_pending() -> None:
    session = session_module.PrivilegedSession("/tmp/acq")
    pending = session_module._PendingRequest()
    session._pending["id"] = pending

    session.close()
    session.close()

    assert pending.error is not None
    assert pending.error.code == "session_closed"


@pytest.mark.unit
def test_session_start_timeout_terminates_process(monkeypatch, tmp_path: Path) -> None:
    askpass = tmp_path / "askpass"
    askpass.write_text("helper")
    monkeypatch.setenv("FIT_LINUX_SUDO_ASKPASS", str(askpass))
    monkeypatch.setattr(session_module.sys, "platform", "linux")
    monkeypatch.setattr(session_module.shutil, "which", lambda _name: "/usr/bin/sudo")
    process = _AliveProcess()
    monkeypatch.setattr(session_module.subprocess, "Popen", lambda *_a, **_k: process)
    session = session_module.PrivilegedSession(str(tmp_path))
    monkeypatch.setattr(session, "_read_stdout", lambda _process: None)
    monkeypatch.setattr(session, "_read_stderr", lambda _process: None)
    monkeypatch.setattr(session, "_watch", lambda *_args: None)
    terminated = []
    monkeypatch.setattr(session, "_terminate", lambda value: terminated.append(value))

    with pytest.raises(PrivilegedProcessError) as exc:
        session.start(timeout=0.01)

    assert exc.value.code == "readiness_timeout"
    assert terminated == [process]


@pytest.mark.unit
def test_session_eof_before_ready_reports_authentication_failure() -> None:
    session = session_module.PrivilegedSession("/tmp/acq")
    process = SimpleNamespace(
        wait=lambda: None,
        returncode=1,
        poll=lambda: 1,
    )
    reader = SimpleNamespace(join=lambda: None)
    session._stderr.extend(b"sudo: authentication failed\n")

    session._watch(process, reader, reader)

    assert session._failure is not None
    assert session._failure.code == "authentication_cancelled"
    assert "authentication failed" in session._failure.details


@pytest.mark.unit
def test_session_cleanup_escalates_from_process_group_term_to_kill(monkeypatch) -> None:
    process = SimpleNamespace(
        pid=4321,
        poll=lambda: None,
        wait=lambda timeout=None: (
            (_ for _ in ()).throw(
                session_module.subprocess.TimeoutExpired("broker", timeout)
            )
            if timeout is not None
            else None
        ),
    )
    signals = []
    monkeypatch.setattr(
        session_module.os,
        "killpg",
        lambda pid, sig: signals.append((pid, sig)),
    )

    session_module.PrivilegedSession("/tmp/acq")._terminate(process)

    assert signals == [
        (4321, session_module.signal.SIGTERM),
        (4321, session_module.signal.SIGKILL),
    ]


@pytest.mark.unit
def test_broker_packet_capture_traceroute_and_shutdown(
    monkeypatch, tmp_path: Path
) -> None:
    output = tmp_path / "capture.pcap"
    requests = [
        {
            "request_id": "1",
            "operation": "start_packet_capture",
            "arguments": {"output_path": str(output)},
        },
        {
            "request_id": "2",
            "operation": "traceroute",
            "arguments": {"destination": "example.org"},
        },
        {
            "request_id": "3",
            "operation": "stop_packet_capture",
            "arguments": {"output_path": str(output)},
        },
        {"request_id": "4", "operation": "shutdown", "arguments": {}},
    ]
    stdin = io.StringIO("".join(json.dumps(item) + "\n" for item in requests))
    stdout = io.StringIO()
    events = []

    class Sniffer:
        def __init__(self):
            self.results = ["packet"]

        def start(self):
            events.append("capture-start")

        def stop(self):
            events.append("capture-stop")

    monkeypatch.setattr(broker_module.scapy, "AsyncSniffer", Sniffer)
    monkeypatch.setattr(
        broker_module.scapy,
        "wrpcap",
        lambda file_object, _packets: file_object.write(
            b"\xd4\xc3\xb2\xa1" + b"\0" * 20
        ),
    )

    def traceroute(_destination, ready):
        ready()
        events.append("traceroute")
        return [{"ttl": 1, "ip": "192.0.2.1", "tcp_response": False}]

    monkeypatch.setattr(broker_module, "run_traceroute", traceroute)

    assert broker_module.PrivilegedBroker(str(tmp_path), stdin, stdout).run() == 0

    messages = [json.loads(line) for line in stdout.getvalue().splitlines()]
    assert messages[0] == {"request_id": None, "status": "session_ready"}
    assert sorted(
        (item["request_id"], item["status"]) for item in messages[1:]
    ) == sorted(
        [
            ("1", "ready"),
            ("2", "ready"),
            ("2", "completed"),
            ("3", "completed"),
            ("4", "completed"),
        ]
    )
    assert events[0] == "capture-start"
    assert set(events[1:]) == {"traceroute", "capture-stop"}


@pytest.mark.unit
def test_broker_rejects_duplicate_capture_stop_without_start_and_traversal(
    monkeypatch, tmp_path: Path
) -> None:
    class Sniffer:
        def __init__(self):
            self.results = []

        def start(self):
            return None

        def stop(self):
            return None

    monkeypatch.setattr(broker_module.scapy, "AsyncSniffer", Sniffer)
    requests = [
        {
            "request_id": "1",
            "operation": "stop_packet_capture",
            "arguments": {"output_path": str(tmp_path / "x")},
        },
        {
            "request_id": "2",
            "operation": "start_packet_capture",
            "arguments": {"output_path": str(tmp_path.parent / "escape.pcap")},
        },
        {
            "request_id": "3",
            "operation": "start_packet_capture",
            "arguments": {"output_path": str(tmp_path / "x.pcap")},
        },
        {
            "request_id": "4",
            "operation": "start_packet_capture",
            "arguments": {"output_path": str(tmp_path / "x.pcap")},
        },
        {"request_id": "5", "operation": "shutdown", "arguments": {}},
    ]
    stdout = io.StringIO()
    broker_module.PrivilegedBroker(
        str(tmp_path),
        io.StringIO("".join(json.dumps(item) + "\n" for item in requests)),
        stdout,
    ).run()
    responses = [json.loads(line) for line in stdout.getvalue().splitlines()][1:]
    errors = {
        item["request_id"]: item.get("error", {}).get("code") for item in responses
    }
    assert errors["1"] == "capture_not_active"
    assert errors["2"] == "invalid_path"
    assert errors["4"] == "capture_active"


@pytest.mark.unit
def test_broker_rejects_malformed_and_non_allowlisted_requests(tmp_path: Path) -> None:
    stdout = io.StringIO()
    stdin = io.StringIO(
        "not-json\n"
        + json.dumps({"request_id": "x", "operation": "shell", "arguments": {}})
        + "\n"
        + json.dumps({"request_id": "z", "operation": "shutdown", "arguments": {}})
        + "\n"
    )
    broker_module.PrivilegedBroker(str(tmp_path), stdin, stdout).run()
    messages = [json.loads(line) for line in stdout.getvalue().splitlines()]
    assert messages[1]["error"]["code"] == "invalid_json"
    assert messages[2]["error"]["code"] == "invalid_operation"
