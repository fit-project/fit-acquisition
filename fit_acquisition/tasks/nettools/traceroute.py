#!/usr/bin/env python3
# -*- coding:utf-8 -*-
######
# -----
# Copyright (c) 2023 FIT-Project
# SPDX-License-Identifier: GPL-3.0-only
# -----
######

import os
from urllib.parse import urlparse
from contextlib import redirect_stdout
import scapy.all as scapy

from shiboken6 import isValid

from PySide6.QtCore import QObject, Signal, QThread, QEventLoop, QTimer

from fit_acquisition.task import Task
from fit_common.gui.utils import State, Status
from fit_acquisition.lang import load_translations


class TracerouteWorker(QObject):
    finished = Signal()
    started = Signal()
    error = Signal(object)

    def __init__(self, parent=None):
        QObject.__init__(self, parent=parent)
        self.translations = load_translations()

    def set_options(self, options):
        self.url = options["url"]
        self.folder = options["acquisition_directory"]

    def __traceroute(self, url, filename):
        try:
            parsed_url = urlparse(url)
            netloc = parsed_url.netloc

            if not netloc:
                self.error.emit(
                    {
                        "title": self.translations["TRACEROUTE_ERROR_TITLE"],
                        "message": self.translations["MALFORMED_URL_ERROR"],
                        "details": "",
                    }
                )
                return

            netloc = netloc.split(":")[0]

            with open(filename, "w") as f:
                with redirect_stdout(f):
                    ans, unans = scapy.sr(
                        scapy.IP(dst=netloc, ttl=(1, 22), id=scapy.RandShort())
                        / scapy.TCP(flags=0x2),
                        timeout=10,
                        verbose=False,
                    )

                    for snd, rcv in ans:
                        print(
                            f"TTL={snd.ttl} IP={rcv.src} TCP_response={isinstance(rcv.payload, scapy.TCP)}"
                        )

            self.finished.emit()

        except Exception as e:
            self.error.emit(
                {
                    "title": self.translations["TRACEROUTE_ERROR_TITLE"],
                    "message": self.translations["TRACEROUTE_EXECUTION_ERROR"],
                    "details": str(e),
                }
            )

    def start(self):
        self.started.emit()
        self.__traceroute(self.url, os.path.join(self.folder, "traceroute.txt"))


class TaskTraceroute(Task):
    def __init__(self, logger, progress_bar=None, status_bar=None, parent=None):
        super().__init__(logger, progress_bar, status_bar, parent)

        self.translations = load_translations()

        self.label = self.translations["TRACEROUTE"]

        self.worker_thread = QThread()
        self.worker = TracerouteWorker()
        self.worker.moveToThread(self.worker_thread)
        self.worker_thread.started.connect(self.worker.start)
        self.worker.started.connect(self.__started)
        self.worker.finished.connect(self.__finished)
        self.worker.error.connect(self.__handle_error)

        self.destroyed.connect(lambda: self.__destroyed_handler(self.__dict__))

    def __handle_error(self, error):
        self.__finished(Status.FAILURE, error.get("details"))

        self.worker_thread.wait()

    def start(self):
        self.worker.set_options(self.options)
        self.update_task(State.STARTED, Status.PENDING)
        self.set_message_on_the_statusbar(self.translations["TRACEROUTE_STARTED"])
        self.worker_thread.start()

    def __started(self):
        self.update_task(State.STARTED, Status.SUCCESS)
        self.started.emit()

    def __finished(self, status=Status.SUCCESS, details=""):
        self.logger.info(
            self.translations["TRACEROUTE_GET_INFO_URL"].format(
                status.name, self.options["url"]
            )
        )
        self.set_message_on_the_statusbar(self.translations["TRACEROUTE_COMPLETED"])
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
