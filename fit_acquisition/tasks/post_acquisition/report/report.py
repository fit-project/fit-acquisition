#!/usr/bin/env python3
# -*- coding:utf-8 -*-
######
# -----
# Copyright (c) 2023 FIT-Project
# SPDX-License-Identifier: GPL-3.0-only
# -----
######


from fit_common.core.utils import get_ntp_date_and_time
from fit_common.gui.utils import Status
from fit_configurations.controller.tabs.network.network_check import (
    NetworkCheckController,
)

from fit_acquisition.tasks.post_acquisition.report.generate import GenerateReport
from fit_acquisition.tasks.task import Task
from fit_acquisition.tasks.task_worker import TaskWorker


class ReportWorker(TaskWorker):

    def start(self):
        self.started.emit()
        report = GenerateReport(
            self.options["acquisition_directory"], self.options["case_info"]
        )
        try:
            report.generate_pdf(
                self.options["type"],
                get_ntp_date_and_time(
                    NetworkCheckController().configuration["ntp_server"]
                ),
            )
            self.finished.emit()
        except Exception as e:
            self.error.emit(
                {
                    "title": self.translations["REPORTFILE"],
                    "message": self.translations["GENERATE_PDF_REPORT_FAILED_MGS"],
                    "details": str(e),
                }
            )


class TaskReport(Task):
    def __init__(self, logger, progress_bar=None, status_bar=None):
        super().__init__(
            logger,
            progress_bar,
            status_bar,
            label="REPORTFILE",
            worker_class=ReportWorker,
        )

    def start(self):
        super().start_task(self.translations["GENERATE_PDF_REPORT_STARTED"])

    def _finished(self, status=Status.SUCCESS, details=""):
        message = self.translations["GENERATE_PDF_REPORT_COMPLETED"].format(status.name)
        super()._finished(status, details, message)
