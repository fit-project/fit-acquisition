#!/usr/bin/env python3
# -*- coding:utf-8 -*-
######
# -----
# Copyright (c) 2023 FIT-Project
# SPDX-License-Identifier: GPL-3.0-only
# -----
######


from shiboken6 import isValid
from PySide6.QtCore import QObject, Signal, QThread, QEventLoop, QTimer


from fit_acquisition.task import Task
from fit_acquisition.tasks.post_acquisition.report.generate import GenerateReport
from fit_common.gui.utils import State, Status
from fit_common.core.utils import get_ntp_date_and_time


from fit_configurations.controller.tabs.network.networkcheck import (
    NetworkControllerCheck,
)

from fit_acquisition.lang import load_translations


class ReportWorker(QObject):
    finished = Signal()
    started = Signal()

    def set_options(self, options):
        self.folder = options["acquisition_directory"]
        self.type = options["type"]
        self.case_info = options["case_info"]

    def start(self):
        self.started.emit()

        report = GenerateReport(self.folder, self.case_info)
        report.generate_pdf(
            self.type,
            get_ntp_date_and_time(NetworkControllerCheck().configuration["ntp_server"]),
        )

        self.finished.emit()


class TaskReport(Task):
    def __init__(self, logger, progress_bar=None, status_bar=None, parent=None):
        super().__init__(logger, progress_bar, status_bar, parent)

        self.translations = load_translations()

        self.label = self.translations["REPORTFILE"]

        self.worker_thread = QThread()
        self.worker = ReportWorker()
        self.worker.moveToThread(self.worker_thread)
        self.worker_thread.started.connect(self.worker.start)
        self.worker.started.connect(self.__started)
        self.worker.finished.connect(self.__finished)

        self.destroyed.connect(lambda: self.__destroyed_handler(self.__dict__))

    def start(self):
        self.worker.set_options(self.options)
        self.update_task(State.STARTED, Status.PENDING)
        self.set_message_on_the_statusbar(
            self.translations["GENERATE_PDF_REPORT_STARTED"]
        )
        self.worker_thread.start()

    def __started(self):
        self.update_task(State.STARTED, Status.SUCCESS)
        self.started.emit()

    def __finished(self):
        self.logger.info(self.translations["GENERATE_PDF_REPORT"])
        self.set_message_on_the_statusbar(
            self.translations["GENERATE_PDF_REPORT_COMPLETED"]
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
