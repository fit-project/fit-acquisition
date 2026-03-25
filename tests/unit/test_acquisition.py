from __future__ import annotations

from collections import defaultdict
from types import SimpleNamespace

import pytest

from fit_acquisition import acquisition as acquisition_module
from fit_acquisition.class_names import class_names


class _SignalStub:
    def connect(self, _callback) -> None:
        return None


class _PostAcquisitionStub:
    def __init__(self) -> None:
        self.finished = _SignalStub()


class _TasksManagerStub:
    def register_task_package(self, _package_name: str) -> None:
        return None

    def load_all_task_modules(self) -> None:
        return None

    def get_tasks(self) -> list:
        return []

    def clear_tasks(self) -> None:
        return None


@pytest.mark.unit
def test_remove_disable_tasks_filters_disabled_network_tools(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        acquisition_module, "load_translations", lambda: defaultdict(str)
    )
    monkeypatch.setattr(acquisition_module, "TasksManager", _TasksManagerStub)
    monkeypatch.setattr(acquisition_module, "PostAcquisition", _PostAcquisitionStub)
    monkeypatch.setattr(
        acquisition_module,
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
        acquisition_module,
        "PacketCaptureController",
        lambda: SimpleNamespace(configuration={"enabled": True}),
    )
    monkeypatch.setattr(
        acquisition_module,
        "ScreenRecorderController",
        lambda: SimpleNamespace(configuration={"enabled_video": True}),
    )
    monkeypatch.setattr(
        acquisition_module,
        "TimestampController",
        lambda: SimpleNamespace(configuration={"enabled": True}),
    )
    monkeypatch.setattr(
        acquisition_module,
        "PecController",
        lambda: SimpleNamespace(configuration={"enabled": True}),
    )

    acquisition = acquisition_module.Acquisition(logger=SimpleNamespace(name="test"))
    filtered = acquisition._Acquisition__remove_disable_tasks(
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
