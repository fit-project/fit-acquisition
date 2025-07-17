# !/usr/bin/env python3
# -*- coding:utf-8 -*-
######
# -----
# Copyright (c) 2023 FIT-Project
# SPDX-License-Identifier: GPL-3.0-only
# -----
######


from fit_common.gui.utils import State, Status
from fit_configurations.controller.tabs.pec.pec import PecController
from PySide6.QtCore import QEventLoop, QTimer, Signal

from fit_acquisition.tasks.post_acquisition.pec.pec import Pec
from fit_acquisition.tasks.task import Task
from fit_acquisition.tasks.task_worker import TaskWorker


class PecAndDownloadEmlWorker(TaskWorker):
    sentpec = Signal()
    downloadedeml = Signal()

    def start(self):
        self.pec_controller = Pec(
            self.options["pec_email"],
            self.options["password"],
            self.options["type"],
            self.options["case_info"],
            self.options["acquisition_directory"],
            self.options["smtp_server"],
            self.options["smtp_port"],
            self.options["imap_server"],
            self.options["imap_port"],
        )
        self.started.emit()
        try:
            self.pec_controller.send_pec()
            self.sentpec.emit()

        except Exception as e:
            print("#################")
            print(str(e))
            self.error.emit(
                {
                    "title": self.translations["LOGIN_FAILED"],
                    "message": self.translations["SMTP_FAILED_MGS"],
                    "details": str(e),
                }
            )

    def download_eml(self):
        for i in range(self.options["retries"]):
            # whait for 8 seconds
            loop = QEventLoop()
            QTimer.singleShot(8000, loop.quit)
            loop.exec()

            try:
                if self.pec_controller.retrieve_eml():
                    self.downloadedeml.emit()
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
    def __init__(self, logger, progress_bar=None, status_bar=None):
        super().__init__(
            logger,
            progress_bar,
            status_bar,
            label="PEC_AND_DOWNLOAD_EML",
            worker_class=PecAndDownloadEmlWorker,
        )

        self.worker.sentpec.connect(self.__on_pec_sent)
        self.worker.downloadedeml.connect(self.__on_eml_downloaded)

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
    
    @Task.options.getter
    def options(self):
        return self._options

    @options.setter
    def options(self, options):
        folder = options["acquisition_directory"]
        case_info = options["case_info"]
        acquisition_type = options["type"]
        options = PecController().configuration
        options["acquisition_directory"] = folder
        options["case_info"] = case_info
        options["type"] = acquisition_type
        self._options = options


    def start(self):
        super().start_task(self.translations["PEC_AND_DOWNLOAD_EML_STARTED"])


    def __on_pec_sent(self):
        sub_task_sent_pec = next(
            (
                task
                for task in self.sub_tasks
                if task["label"] == self.translations["PEC"]
            ),
            None,
        )
        if sub_task_sent_pec:
            sub_task_sent_pec["state"] = State.COMPLETED
            sub_task_sent_pec["status"] = Status.SUCCESS

        self.logger.info(
            self.translations["PEC_SENT"].format(
                self.worker.options["pec_email"], Status.SUCCESS.name
            )
        )
        self.set_message_on_the_statusbar(
            self.translations["PEC_SENT"].format(
                self.worker.options["pec_email"], Status.SUCCESS.name
            )
        )
        self.update_progress_bar()

        self.worker.download_eml()


    def __on_eml_downloaded(self):
        sub_task_download_eml = next(
            (
                task
                for task in self.sub_tasks
                if task["label"] == self.translations["EML"]
            ),
            None,
        )
        if sub_task_download_eml:
            sub_task_download_eml["state"] = State.COMPLETED
            sub_task_download_eml["status"] = Status.SUCCESS
        
        message = self.translations["EML_DOWNLOAD"].format(Status.SUCCESS.name)

        super()._finished(message=message)