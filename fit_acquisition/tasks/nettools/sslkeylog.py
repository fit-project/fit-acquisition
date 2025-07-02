#!/usr/bin/env python3
# -*- coding:utf-8 -*-
######
# -----
# Copyright (c) 2023 FIT-Project
# SPDX-License-Identifier: GPL-3.0-only
# -----
######

import os
from shiboken6 import isValid

from PySide6.QtCore import QObject, Signal, QThread, QEventLoop, QTimer

from fit_acquisition.task import Task
from fit_common.gui.utils import State, Status
from fit_acquisition.lang import load_translations


class SSLKeyLogWorker(QObject):
    finished = Signal()
    started = Signal()

    @property
    def folder(self):
        return self._folder

    @folder.setter
    def folder(self, folder):
        self._folder = folder

    def start(self):
        self.started.emit()
        os.environ["SSLKEYLOGFILE"] = os.path.join(self.folder, "sslkey.log")
        self.finished.emit()


class TaskSSLKeyLog(Task):
    def __init__(self, logger, progress_bar=None, status_bar=None, parent=None):
        super().__init__(logger, progress_bar, status_bar, parent)

        self.translations = load_translations()

        self.label = self.translations["SSLKEYLOG"]

        self.worker_thread = QThread()
        self.worker = SSLKeyLogWorker()
        self.worker.moveToThread(self.worker_thread)
        self.worker_thread.started.connect(self.worker.start)
        self.worker.started.connect(self.__started)
        self.worker.finished.connect(self.__finished)

        self.destroyed.connect(lambda: self.__destroyed_handler(self.__dict__))

    def start(self):
        self.worker.folder = self.options["acquisition_directory"]
        self.update_task(State.STARTED, Status.PENDING)
        self.set_message_on_the_statusbar(self.translations["SSLKEYLOG_STARTED"])
        self.worker_thread.start()

    def __started(self):
        self.update_task(State.STARTED, Status.SUCCESS)
        self.started.emit()

    def __finished(self):
        self.logger.info(
            self.translations["SSLKEYLOG_COMPLETED"].format(Status.SUCCESS.name)
        )
        self.set_message_on_the_statusbar(
            self.translations["SSLKEYLOG_COMPLETED"].format(Status.SUCCESS.name)
        )
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
