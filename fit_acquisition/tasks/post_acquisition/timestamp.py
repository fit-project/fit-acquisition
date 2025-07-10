#!/usr/bin/env python3
# -*- coding:utf-8 -*-
######
# -----
# Copyright (c) 2023 FIT-Project
# SPDX-License-Identifier: GPL-3.0-only
# -----
######

import os

import requests
from rfc3161ng.api import RemoteTimestamper


from shiboken6 import isValid


from PySide6.QtCore import QObject, Signal, QThread, QEventLoop, QTimer


from fit_acquisition.task import Task
from fit_common.gui.utils import State, Status
from fit_acquisition.lang import load_translations

from fit_configurations.controller.tabs.timestamp.timestamp import (
    Timestamp as TimestampController,
)


class TimestampWorker(QObject):
    finished = Signal()
    started = Signal()

    def __init__(self):
        QObject.__init__(self)

    def set_options(self, options):
        self.server_name = options["server_name"]
        self.cert_url = options["cert_url"]
        self.acquisition_directory = options["acquisition_directory"]
        self.pdf_filename = options["pdf_filename"]

    def apply_timestamp(self):
        self.started.emit()
        pdf_path = os.path.join(self.acquisition_directory, self.pdf_filename)
        ts_path = os.path.join(self.acquisition_directory, "timestamp.tsr")
        cert_path = os.path.join(self.acquisition_directory, "tsa.crt")

        # getting the chain from the authority
        response = requests.get(self.cert_url)
        with open(cert_path, "wb") as f:
            f.write(response.content)

        with open(cert_path, "rb") as f:
            certificate = f.read()

        # create the object
        rt = RemoteTimestamper(
            self.server_name, certificate=certificate, hashname="sha256"
        )

        # file to be certificated
        with open(pdf_path, "rb") as f:
            timestamp = rt.timestamp(data=f.read())

        # saving the timestamp
        with open(ts_path, "wb") as f:
            f.write(timestamp)

        self.finished.emit()


class TaskTimestamp(Task):
    def __init__(self, logger, progress_bar=None, status_bar=None):
        super().__init__(logger, progress_bar, status_bar)

        self.translations = load_translations()

        self.label = self.translations["TIMESTAMP"]

        self.worker_thread = QThread()
        self.worker = TimestampWorker()
        self.worker.moveToThread(self.worker_thread)
        self.worker_thread.started.connect(self.worker.apply_timestamp)
        self.worker.started.connect(self.__started)
        self.worker.finished.connect(self.__finished)

        self.destroyed.connect(lambda: self.__destroyed_handler(self.__dict__))

    @Task.options.getter
    def options(self):
        return self._options

    @options.setter
    def options(self, options):
        folder = options["acquisition_directory"]
        pdf_filename = options["pdf_filename"]
        options = TimestampController().options
        options["acquisition_directory"] = folder
        options["pdf_filename"] = pdf_filename
        self._options = options

    def start(self):
        self.worker.set_options(self.options)
        self.update_task(State.STARTED, Status.PENDING)
        self.set_message_on_the_statusbar(self.translations["TIMESTAMP_STARTED"])
        self.worker_thread.start()

    def __started(self):
        self.update_task(State.STARTED, Status.SUCCESS)
        self.started.emit()

    def __finished(self):
        self.logger.info(
            self.translations["TIMESTAMP_APPLY"].format(
                Status.SUCCESS.name,
                self.options["pdf_filename"],
                self.options["server_name"],
            )
        )
        self.set_message_on_the_statusbar(self.translations["TIMESTAMP_COMPLETED"])
        self.update_progress_bar()

        self.update_task(State.COMPLETED, Status.SUCCESS)

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
