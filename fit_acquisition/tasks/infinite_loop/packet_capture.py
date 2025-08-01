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

import scapy.all as scapy
from fit_common.core import debug, get_context, log_exception
from fit_common.gui.utils import Status
from fit_configurations.controller.tabs.packet_capture.packet_capture import (
    PacketCaptureController,
)
from PySide6.QtCore import QEventLoop, QTimer

from fit_acquisition.tasks.task import Task
from fit_acquisition.tasks.task_worker import TaskWorker

logging.getLogger("scapy").setLevel(logging.CRITICAL)


class PacketCaptureWorker(TaskWorker):

    def __init__(self):
        super().__init__()
        self.output_file = None
        self.sniffer = scapy.AsyncSniffer()

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
        self.started.emit()
        try:
            self.sniffer.start()
        except Exception as e:
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
                    "details": str(e),
                }
            )

    def stop(self):
        try:
            self.sniffer.stop()
            loop = QEventLoop()
            QTimer.singleShot(1000, loop.quit)
            loop.exec()
            scapy.wrpcap(self.options.get("output_file"), self.sniffer.results)
            self.finished.emit()
        except Exception as e:
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
                    "details": str(e),
                }
            )


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
