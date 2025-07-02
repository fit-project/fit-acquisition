# !/usr/bin/env python3
# -*- coding:utf-8 -*-
######
# -----
# Copyright (c) 2023 FIT-Project
# SPDX-License-Identifier: GPL-3.0-only
# -----
######

from shiboken6 import isValid
from enum import Enum

from PySide6.QtCore import QObject, Signal, QThread, QEventLoop, QTimer


from fit_acquisition.task import Task
from fit_common.gui.utils import State, Status
from fit_acquisition.lang import load_translations

from fit_configurations.controller.tabs.pec.pec import Pec as PecConfigController


from fit_acquisition.tasks.post_acquisition.pec.pec import Pec


class PecAndDownloadEmlWorker(QObject):
    sentpec = Signal(Enum)
    downloadedeml = Signal(str)
    error = Signal(object)
    started = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.translations = load_translations()

    def set_options(self, options):
        self.options = PecConfigController().options
        self.options["case_info"] = options["case_info"]
        self.options["acquisition_directory"] = options["acquisition_directory"]
        self.options["type"] = options["type"]

    def send(self):
        status = Status.SUCCESS

        self.pec_controller = Pec(
            self.options.get("pec_email"),
            self.options.get("password"),
            self.options.get("type"),
            self.options.get("case_info"),
            self.options.get("acquisition_directory"),
            self.options.get("smtp_server"),
            self.options.get("smtp_port"),
            self.options.get("imap_server"),
            self.options.get("imap_port"),
        )
        self.started.emit()
        try:
            self.pec_controller.send_pec()
            self.sentpec.emit(status)

        except Exception as e:

            status = Status.FAILURE
            self.error.emit(
                {
                    "title": self.translations["LOGIN_FAILED"],
                    "message": self.translations["SMTP_FAILED_MGS"],
                    "details": str(e),
                }
            )

    def download_eml(self):
        for i in range(self.options.get("retries")):
            status = Status.FAILURE

            # whait for 8 seconds
            loop = QEventLoop()
            QTimer.singleShot(8000, loop.quit)
            loop.exec()

            try:
                if self.pec_controller.retrieve_eml():
                    status = Status.SUCCESS
                    self.downloadedeml.emit(status)
                    break
            except Exception as e:
                self.error.emit(
                    {
                        "title": self.translations["LOGIN_FAILED"],
                        "message": self.translations["IMAP_FAILED_MGS"],
                        "details": str(e),
                    }
                )
                break


class TaskPecAndDownloadEml(Task):
    def __init__(self, logger, progress_bar=None, status_bar=None, parent=None):
        super().__init__(logger, progress_bar, status_bar, parent)

        self.translations = load_translations()

        self.label = self.translations["PEC_AND_DOWNLOAD_EML"]

        self.worker_thread = QThread()
        self.worker = PecAndDownloadEmlWorker()
        self.worker.moveToThread(self.worker_thread)
        self.worker_thread.started.connect(self.worker.send)
        self.worker.started.connect(self.__started)
        self.worker.sentpec.connect(self.__is_pec_sent)
        self.worker.error.connect(self.__handle_error)
        self.worker.downloadedeml.connect(self.__is_eml_downloaded)
        self.sub_tasks = [
            {
                "label": self.translations["PEC"],
                "state": self.state,
                "status": self.status,
            },
            {
                "label": self.translations["EML"],
                "state": self.state,
                "status": self.status,
            },
        ]

        self.destroyed.connect(lambda: self.__destroyed_handler(self.__dict__))

    def __handle_error(self, error):
        print("ma succede qualcosa")
        self.__finished(Status.FAILURE, error.get("details"))

    def start(self):
        self.worker.set_options(self.options)
        self.update_task(State.STARTED, Status.PENDING)
        self.set_message_on_the_statusbar(
            self.translations["PEC_AND_DOWNLOAD_EML_STARTED"]
        )
        self.worker_thread.start()

    def __started(self):
        self.update_task(State.STARTED, Status.SUCCESS)
        self.started.emit()

    def __is_pec_sent(self, status):
        sub_task_sent_pec = next(
            (
                task
                for task in self.sub_tasks
                if task.get("label") == self.translations["PEC"]
            ),
            None,
        )
        if sub_task_sent_pec:
            sub_task_sent_pec["state"] = State.COMPLETED
            sub_task_sent_pec["status"] = status

        self.logger.info(
            self.translations["PEC_SENT"].format(
                self.worker.options.get("pec_email"), status.value
            )
        )
        self.set_message_on_the_statusbar(
            self.translations["PEC_SENT"].format(
                self.worker.options.get("pec_email"), status.value
            )
        )
        self.update_progress_bar()

        if status == Status.SUCCESS:
            self.worker.download_eml()
        else:
            self.logger.info(
                self.translations["PEC_HAS_NOT_BEEN_SENT_CANNOT_DOWNLOAD_EML"]
            )
            self.__finished()

    def __is_eml_downloaded(self, status):
        sub_task_download_eml = next(
            (
                task
                for task in self.sub_tasks
                if task.get("label") == self.translations["EML"]
            ),
            None,
        )
        if sub_task_download_eml:
            sub_task_download_eml["state"] = State.COMPLETED
            sub_task_download_eml["status"] = status

        self.set_message_on_the_statusbar(
            self.translations["EML_DOWNLOAD"].format(status)
        )
        self.update_progress_bar()
        self.__finished()

    def __finished(self, status=Status.SUCCESS, details=""):

        self.set_message_on_the_statusbar(
            self.translations["PEC_AND_DOWNLOAD_EML_COMPLETED"].format(status.name)
        )
        self.logger.info(
            self.translations["PEC_AND_DOWNLOAD_EML_COMPLETED"].format(status.name)
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
