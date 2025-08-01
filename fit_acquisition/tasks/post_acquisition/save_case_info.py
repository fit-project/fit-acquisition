#!/usr/bin/env python3
# -*- coding:utf-8 -*-
######
# -----
# Copyright (c) 2023 FIT-Project
# SPDX-License-Identifier: GPL-3.0-only
# -----
######

import base64
import json
import os

from fit_common.core import debug, get_context, log_exception
from fit_common.gui.utils import Status

from fit_acquisition.tasks.task import Task
from fit_acquisition.tasks.task_worker import TaskWorker


class SaveCaseInfoWorker(TaskWorker):

    def start(self):
        self.started.emit()
        try:
            file = os.path.join(
                self.options.get("acquisition_directory"), "caseinfo.json"
            )
            case_info = self.options["case_info"]
            logo_bin = case_info["logo_bin"]

            if logo_bin:
                __logo_bin = base64.b64encode(logo_bin)
                case_info["logo_bin"] = str(__logo_bin, encoding="utf-8")

            with open(file, "w") as f:
                json.dump(self.options.get("case_info"), f, ensure_ascii=False)

            case_info["logo_bin"] = logo_bin

            self.finished.emit()

        except Exception as e:
            log_exception(e, context=get_context(self))
            debug(
                "Start save case info failed",
                str(e),
                context=get_context(self),
            )
            self.error.emit(
                {
                    "title": self.translations["SAVE_CASE_INFO_ERROR_TITLE"],
                    "message": self.translations["SAVE_CASE_INFO_EXECUTION_ERROR"],
                    "details": str(e),
                }
            )


class TaskSaveCaseInfo(Task):
    def __init__(self, logger, progress_bar=None, status_bar=None):
        super().__init__(
            logger,
            progress_bar,
            status_bar,
            label="SAVE_CASE_INFO",
            worker_class=SaveCaseInfoWorker,
        )

    def start(self):
        super().start_task(self.translations["SAVE_CASE_INFO_STARTED"])

    def _finished(self, status=Status.SUCCESS, details=""):
        message = self.translations["SAVE_CASE_INFO_COMPLETED"].format(status.name)

        super()._finished(status, details, message)
