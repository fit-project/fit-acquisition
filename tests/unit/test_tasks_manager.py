from __future__ import annotations

from types import SimpleNamespace

import pytest

from fit_acquisition.class_names import class_names
from fit_acquisition.tasks import tasks_manager as manager_module


@pytest.mark.unit
def test_register_task_package_accepts_only_strings() -> None:
    manager = manager_module.TasksManager()
    manager.task_package_names.clear()

    manager.register_task_package("fit_acquisition.tasks.network_tools")
    manager.register_task_package(123)  # type: ignore[arg-type]

    assert manager.task_package_names == ["fit_acquisition.tasks.network_tools"]


@pytest.mark.unit
def test_is_enabled_tasks_filters_disabled_network_tools(monkeypatch: pytest.MonkeyPatch) -> None:
    manager = manager_module.TasksManager()

    monkeypatch.setattr(
        manager_module,
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
        manager_module,
        "PacketCaptureController",
        lambda: SimpleNamespace(configuration={"enabled": True}),
    )
    monkeypatch.setattr(
        manager_module,
        "ScreenRecorderController",
        lambda: SimpleNamespace(configuration={"enabled": True}),
    )
    monkeypatch.setattr(
        manager_module,
        "TimestampController",
        lambda: SimpleNamespace(configuration={"enabled": True}),
    )
    monkeypatch.setattr(
        manager_module,
        "PecController",
        lambda: SimpleNamespace(configuration={"enabled": True}),
    )

    filtered = manager.is_enabled_tasks(
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
def test_get_tasks_from_class_name_returns_existing_only() -> None:
    manager = manager_module.TasksManager()
    manager.clear_tasks()

    class _TaskA:
        pass

    class _TaskB:
        pass

    a = _TaskA()
    b = _TaskB()
    manager.task_handler.add_task(a)
    manager.task_handler.add_task(b)

    found = manager.get_tasks_from_class_name(["_TaskA", "Missing", "_TaskB"])

    assert found == [a, b]
