#!/usr/bin/env python3
# -*- coding:utf-8 -*-
######
# -----
# Copyright (c) 2023 FIT-Project
# SPDX-License-Identifier: GPL-3.0-only
# -----
######

import os
import json
import base64
import os


from shiboken6 import isValid


from PySide6.QtCore import QObject, Signal, QThread, QEventLoop, QTimer


from fit_acquisition.task import Task
from fit_common.gui.utils import State, Status
from fit_acquisition.lang import load_translations


class SaveCaseInfoWorker(QObject):
    finished = Signal()
    started = Signal()

    @property
    def options(self):
        return self._options

    @options.setter
    def options(self, options):
        self._options = options

    def start(self):
        self.started.emit()
        file = os.path.join(self.options.get("acquisition_directory"), "caseinfo.json")
        case_info = self.options.get("case_info")
        logo_bin = case_info.get("logo_bin")

        if logo_bin:
            __logo_bin = base64.b64encode(logo_bin)
            case_info["logo_bin"] = str(__logo_bin, encoding="utf-8")

        with open(file, "w") as f:
            json.dump(self.options.get("case_info"), f, ensure_ascii=False)

        case_info["logo_bin"] = logo_bin

        self.finished.emit()


class TaskSaveCaseInfo(Task):
    def __init__(self, logger, progress_bar=None, status_bar=None, parent=None):
        super().__init__(logger, progress_bar, status_bar, parent)

        self.translations = load_translations()

        self.label = self.translations["SAVE_CASE_INFO"]

        self.worker_thread = QThread()
        self.worker = SaveCaseInfoWorker()
        self.worker.moveToThread(self.worker_thread)
        self.worker_thread.started.connect(self.worker.start)
        self.worker.started.connect(self.__started)
        self.worker.finished.connect(self.__finished)

        self.destroyed.connect(lambda: self.__destroyed_handler(self.__dict__))

    def start(self):
        self.update_task(State.STARTED, Status.PENDING)
        self.set_message_on_the_statusbar(self.translations["SAVE_CASE_INFO_STARTED"])
        self.worker.options = self.options
        self.worker_thread.start()

    def __started(self):
        self.update_task(State.STARTED, Status.SUCCESS)
        self.started.emit()

    def __finished(self):
        self.logger.info(self.translations["SAVE_CASE_INFO"])
        self.set_message_on_the_statusbar(self.translations["SAVE_CASE_INFO_COMPLETED"])
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
