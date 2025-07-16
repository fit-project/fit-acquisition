#!/usr/bin/env python3
# -*- coding:utf-8 -*-
######
# -----
# Copyright (c) 2023 FIT-Project
# SPDX-License-Identifier: GPL-3.0-only
# -----
######

import os

from fit_common.gui.utils import Status

from fit_acquisition.tasks.task import Task
from fit_acquisition.tasks.task_worker import TaskWorker


class SSLKeyLogWorker(TaskWorker):
    def start(self):
        self.started.emit()
        os.environ["SSLKEYLOGFILE"] = os.path.join(self.options["acquisition_directory"], "sslkey.log")
        self.finished.emit()


class TaskSSLKeyLog(Task):
    def __init__(self, logger, progress_bar=None, status_bar=None):
        super().__init__(
            logger,
            progress_bar,
            status_bar,
            label="SSLKEYLOG",
            worker_class=SSLKeyLogWorker,
        )
    
    def start(self):
        super().start_task(self.translations["SSLKEYLOG_STARTED"])
    

    def _finished(self, status=Status.SUCCESS, details=""):
         print("ci centra 2")
         super()._finished(status, details, self.translations["SSLKEYLOG_COMPLETED"].format(Status.SUCCESS.name))