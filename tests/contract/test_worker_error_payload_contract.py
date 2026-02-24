from __future__ import annotations

import pytest

from fit_acquisition.tasks.network_tools import headers as headers_module
from fit_acquisition.tasks.network_tools import nslookup as nslookup_module
from fit_acquisition.tasks.network_tools import traceroute as traceroute_module
from fit_acquisition.tasks.network_tools import whois as whois_module


@pytest.mark.contract
@pytest.mark.parametrize(
    ("worker", "options"),
    [
        (headers_module.HeadersWorker(), {"url": "invalid"}),
        (
            nslookup_module.NslookupWorker(),
            {
                "url": "invalid",
                "nslookup_dns_server": "1.1.1.1",
                "nslookup_enable_verbose_mode": False,
                "nslookup_enable_tcp": False,
            },
        ),
        (traceroute_module.TracerouteWorker(), {"url": "invalid", "acquisition_directory": "/tmp"}),
        (whois_module.WhoisWorker(), {"url": "###"}),
    ],
)
def test_worker_error_signal_payload_contract(worker, options) -> None:
    worker.options = options
    payloads: list[dict] = []
    worker.error.connect(lambda payload: payloads.append(payload))

    worker.start()

    assert len(payloads) == 1
    payload = payloads[0]
    assert set(payload.keys()) == {"title", "message", "details"}
    assert all(isinstance(payload[key], str) for key in payload)
    assert payload["title"]
    assert payload["message"]
    assert payload["details"]
