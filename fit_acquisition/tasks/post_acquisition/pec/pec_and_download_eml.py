# !/usr/bin/env python3
# -*- coding:utf-8 -*-
######
# -----
# Copyright (c) 2023 FIT-Project
# SPDX-License-Identifier: GPL-3.0-only
# -----
######

from PyQt6 import QtWidgets
from PyQt6.QtCore import QObject, pyqtSignal, QThread, QEventLoop, QTimer
from common.constants.view.tasks import labels, state, status

from view.tasks.task import Task
from view.tasks.class_names import *
from view.error import Error as ErrorView

from controller.pec import Pec as PecController
from controller.configurations.tabs.pec.pec import Pec as PecConfigController

from common.constants.view.pec import pec
from common.constants import logger


class PecAndDownloadEmlWorker(QObject):
    sentpec = pyqtSignal(str)
    downloadedeml = pyqtSignal(str)
    error = pyqtSignal(object)
    started = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)

    def set_options(self, options):
        self.options = PecConfigController().options
        self.options["case_info"] = options["case_info"]
        self.options["acquisition_directory"] = options["acquisition_directory"]
        self.options["type"] = options["type"]

    def send(self):
        __status = status.SUCCESS

        self.pec_controller = PecController(
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

        except Exception as e:
            __status = status.FAIL
            self.error.emit(
                {
                    "title": pec.LOGIN_FAILED,
                    "message": pec.SMTP_FAILED_MGS,
                    "details": str(e),
                }
            )

        self.sentpec.emit(__status)

    def download_eml(self):
        for i in range(self.options.get("retries")):
            __status = status.FAIL

            # whait for 8 seconds
            loop = QEventLoop()
            QTimer.singleShot(8000, loop.quit)
            loop.exec()

            try:
                if self.pec_controller.retrieve_eml():
                    __status = status.SUCCESS
                    break
            except Exception as e:
                self.error.emit(
                    {
                        "title": pec.LOGIN_FAILED,
                        "message": pec.IMAP_FAILED_MGS,
                        "details": str(e),
                    }
                )
                break

        self.downloadedeml.emit(__status)


class TaskPecAndDownloadEml(Task):
    def __init__(self, logger, progress_bar=None, status_bar=None, parent=None):
        super().__init__(logger, progress_bar, status_bar, parent)

        self.label = labels.PEC_AND_DOWNLOAD_EML
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
                "label": labels.PEC,
                "state": self.state,
                "status": self.status,
            },
            {
                "label": labels.EML,
                "state": self.state,
                "status": self.status,
            },
        ]

        self.destroyed.connect(lambda: self.__destroyed_handler(self.__dict__))

    def start(self):
        self.worker.set_options(self.options)
        self.update_task(state.STARTED, status.PENDING)
        self.set_message_on_the_statusbar(logger.PEC_AND_DOWNLOAD_EML_STARTED)
        self.worker_thread.start()

    def __handle_error(self, error):
        error_dlg = ErrorView(
            QtWidgets.QMessageBox.Icon.Critical,
            error.get("title"),
            error.get("message"),
            error.get("details"),
        )
        error_dlg.exec()

    def __started(self):
        self.update_task(state.STARTED, status.SUCCESS)
        self.started.emit()

    def __is_pec_sent(self, __status):
        sub_task_sent_pec = next(
            (task for task in self.sub_tasks if task.get("label") == labels.PEC), None
        )
        if sub_task_sent_pec:
            sub_task_sent_pec["state"] = state.COMPLETED
            sub_task_sent_pec["status"] = __status

        self.logger.info(
            logger.PEC_SENT.format(self.worker.options.get("pec_email"), __status)
        )
        self.set_message_on_the_statusbar(
            logger.PEC_SENT.format(self.worker.options.get("pec_email"), __status)
        )
        self.upadate_progress_bar()

        if __status == status.SUCCESS:
            self.worker.download_eml()
        else:
            self.logger.info(logger.PEC_HAS_NOT_BEEN_SENT_CANNOT_DOWNLOAD_EML)
            self.__finished()

    def __is_eml_downloaded(self, __status):
        sub_task_download_eml = next(
            (task for task in self.sub_tasks if task.get("label") == labels.EML), None
        )
        if sub_task_download_eml:
            sub_task_download_eml["state"] = state.COMPLETED
            sub_task_download_eml["status"] = __status

        self.set_message_on_the_statusbar(logger.EML_DOWNLOAD.format(__status))
        self.upadate_progress_bar()
        self.__finished()

    def __finished(self):
        self.label = labels.PEC_AND_DOWNLOAD_EML
        self.set_message_on_the_statusbar(logger.PEC_AND_DOWNLOAD_EML_COMPLETED)
        self.upadate_progress_bar()

        self.update_task(state.COMPLETED, status.SUCCESS)

        self.finished.emit()

        self.worker_thread.quit()
        self.worker_thread.wait()

    def __destroyed_handler(self, _dict):
        if self.worker_thread.isRunning():
            self.worker_thread.quit()
            self.worker_thread.wait()
