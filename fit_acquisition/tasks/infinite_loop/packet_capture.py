#!/usr/bin/env python3
# -*- coding:utf-8 -*-
######
# -----
# Copyright (c) 2023 FIT-Project
# SPDX-License-Identifier: GPL-3.0-only
# -----
######

import logging
from shiboken6 import isValid

logging.getLogger("scapy").setLevel(logging.CRITICAL)
import scapy.all as scapy

import os

from PySide6.QtCore import QObject, QEventLoop, QTimer, Signal, QThread

from fit_acquisition.task import Task
from fit_acquisition.task_worker import TaskWorker


from fit_configurations.controller.tabs.packetcapture.packetcapture import (
    PacketCapture as PacketCaptureCotroller,
)


from fit_common.gui.utils import State, Status


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
            self.error.emit(
                {
                    "title": self.translations["PACKET_CAPTURE"],
                    "message": self.translations["PACKET_CAPTURE_ERROR"],
                    "details": str(e),
                }
            )


class TaskPacketCapture(Task):
    def __init__(self, logger, progress_bar=None, status_bar=None):
        super().__init__(logger, progress_bar, status_bar)

        self.label = self.translations["PACKET_CAPTURE"]
        self.is_infinite_loop = True

        self.worker_thread = QThread()
        self.worker = PacketCaptureWorker()
        self.worker.moveToThread(self.worker_thread)

        self.worker_thread.started.connect(self.worker.start)

        self.worker.started.connect(self.__started)
        self.worker.finished.connect(self.__finished)
        self.worker.error.connect(self.__handle_error)
        self.destroyed.connect(lambda: self.__destroyed_handler(self.__dict__))

    @Task.options.getter
    def options(self):
        return self._options

    @options.setter
    def options(self, options):
        folder = options["acquisition_directory"]
        options = PacketCaptureCotroller().options
        options["acquisition_directory"] = folder
        self._options = options

    def __handle_error(self, error):
        self.__finished(Status.FAILURE, error.get("details"))

    def start(self):
        self.update_task(State.STARTED, Status.PENDING)
        self.set_message_on_the_statusbar(
            self.translations["NETWORK_PACKET_CAPTURE_STARTED"]
        )

        self.worker.options = self.options
        self.worker_thread.start()

    def __started(self):
        self.update_task(
            State.STARTED,
            Status.SUCCESS,
            self.translations["NETWORK_PACKET_CAPTURE_STARTED_DETAILS"],
        )

        self.started.emit()

    def stop(self):
        self.update_task(State.STOPPED, Status.PENDING)
        self.set_message_on_the_statusbar(
            self.translations["NETWORK_PACKET_CAPTURE_STOPPED"]
        )
        self.worker.stop()

    def __finished(self, status=Status.SUCCESS, details=""):

        if status == Status.SUCCESS:
            details = self.translations["NETWORK_PACKET_CAPTURE_COMPLETED_DETAILS"]

        self.logger.info(
            self.translations["NETWORK_PACKET_CAPTURE_COMPLETED"].format(status.name)
        )
        self.set_message_on_the_statusbar(
            self.translations["NETWORK_PACKET_CAPTURE_COMPLETED"]
        )
        self.update_progress_bar()
        self.update_task(State.COMPLETED, status, details)

        self.finished.emit()

        loop = QEventLoop()
        QTimer.singleShot(1000, loop.quit)
        loop.exec()

        self.worker_thread.quit()
        self.worker_thread.wait()

    def __destroyed_handler(self, _dict):
        if hasattr(self, "worker_thread") and isValid(self.worker_thread):
            if self.worker_thread.isRunning():
                self.worker_thread.quit()
                self.worker_thread.wait()
