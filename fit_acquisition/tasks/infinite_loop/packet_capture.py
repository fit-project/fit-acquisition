#!/usr/bin/env python3
# -*- coding:utf-8 -*-
######
# -----
# Copyright (c) 2023 FIT-Project
# SPDX-License-Identifier: GPL-3.0-only
# -----
######

import logging
import os
import sys
from pathlib import Path

import scapy.all as scapy
from fit_common.core import debug, get_context, log_exception
from fit_common.gui.utils import Status
from fit_configurations.controller.tabs.packet_capture.packet_capture import (
    PacketCaptureController,
)
from PySide6.QtCore import QEventLoop, QTimer

from fit_acquisition.privileged.runner import (
    PrivilegedProcessError,
    PrivilegedRunner,
)
from fit_acquisition.tasks.task import Task
from fit_acquisition.tasks.task_worker import TaskWorker

logging.getLogger("scapy").setLevel(logging.CRITICAL)

_PCAP_MAGIC_NUMBERS = {
    b"\xa1\xb2\xc3\xd4",
    b"\xd4\xc3\xb2\xa1",
    b"\xa1\xb2\x3c\x4d",
    b"\x4d\x3c\xb2\xa1",
}


class PacketCaptureWorker(TaskWorker):

    def __init__(self):
        super().__init__()
        self.output_file = None
        self.sniffer = None
        self.privileged_runner = None

    @TaskWorker.options.getter
    def options(self):
        return self._options

    @options.setter
    def options(self, options):
        options["output_file"] = os.path.join(
            options["acquisition_directory"], options["filename"]
        )
        self._options = options

    def start(self):
        try:
            if sys.platform == "linux":
                if self.privilege_authorization is None:
                    raise PrivilegedProcessError(
                        "authorization_unavailable",
                        "Privilege authorization is unavailable",
                    )
                self.privilege_authorization.require("packet_capture")
                self.privileged_runner = PrivilegedRunner()
                self.privileged_runner.start("packet-capture", [])
                self.started.emit()
                return
            if self.sniffer is None:
                self.sniffer = scapy.AsyncSniffer()
            self.sniffer.start()
            self.started.emit()
        except Exception as e:
            details = (
                f"{e.code}: {e.details}"
                if isinstance(e, PrivilegedProcessError)
                else str(e)
            )
            log_exception(e, context=get_context(self))
            debug(
                "Start packet capture failed",
                str(e),
                context=get_context(self),
            )
            self.error.emit(
                {
                    "title": self.translations["PACKET_CAPTURE"],
                    "message": self.translations["PACKET_CAPTURE_ERROR"],
                    "details": details,
                }
            )
            if self.privileged_runner is not None:
                self.privileged_runner.cancel()
                self.privileged_runner = None

    def stop(self):
        try:
            if sys.platform == "linux" and self.privileged_runner is not None:
                self.privileged_runner.cancel()
                pcap = self.privileged_runner.wait(timeout=10)
                if len(pcap) < 24 or pcap[:4] not in _PCAP_MAGIC_NUMBERS:
                    raise PrivilegedProcessError(
                        "invalid_output",
                        "Privileged packet capture returned an invalid PCAP",
                    )
                output = Path(self.options["output_file"])
                base = Path(self.options["acquisition_directory"]).resolve()
                resolved = output.resolve()
                if resolved.parent != base or output.name != self.options["filename"]:
                    raise ValueError("Invalid packet capture output path")
                resolved.write_bytes(pcap)
                self.finished.emit()
                self.privileged_runner = None
                return
            if self.sniffer is None:
                self.finished.emit()
                return
            self.sniffer.stop()
            loop = QEventLoop()
            QTimer.singleShot(1000, loop.quit)
            loop.exec()
            scapy.wrpcap(self.options.get("output_file"), self.sniffer.results)
            self.finished.emit()
            self.sniffer = None
        except Exception as e:
            details = (
                f"{e.code}: {e.details}"
                if isinstance(e, PrivilegedProcessError)
                else str(e)
            )
            log_exception(e, context=get_context(self))
            debug(
                "Stop packet capture failed",
                str(e),
                context=get_context(self),
            )
            self.error.emit(
                {
                    "title": self.translations["PACKET_CAPTURE"],
                    "message": self.translations["PACKET_CAPTURE_ERROR"],
                    "details": details,
                }
            )
            if self.privileged_runner is not None:
                self.privileged_runner.cancel()
                self.privileged_runner = None

    def cancel(self):
        if self.privileged_runner is not None:
            self.privileged_runner.cancel()


class TaskPacketCapture(Task):
    def __init__(self, logger, progress_bar=None, status_bar=None):
        super().__init__(
            logger,
            progress_bar,
            status_bar,
            label="PACKET_CAPTURE",
            is_infinite_loop=True,
            worker_class=PacketCaptureWorker,
        )

    @Task.options.getter
    def options(self):
        return self._options

    @options.setter
    def options(self, options):
        folder = options["acquisition_directory"]
        options = PacketCaptureController().configuration
        options["acquisition_directory"] = folder
        self._options = options

    def start(self):
        super().start_task(self.translations["NETWORK_PACKET_CAPTURE_STARTED"])

    def stop(self):
        super().stop_task(self.translations["NETWORK_PACKET_CAPTURE_STOPPED"])

    def _started(self):
        super()._started(self.translations["NETWORK_PACKET_CAPTURE_STARTED_DETAILS"])

    def _finished(self, status=Status.SUCCESS, details=""):

        if status == Status.SUCCESS:
            details = self.translations["NETWORK_PACKET_CAPTURE_COMPLETED_DETAILS"]

        super()._finished(
            status,
            details,
            self.translations["NETWORK_PACKET_CAPTURE_COMPLETED"].format(status.name),
        )
