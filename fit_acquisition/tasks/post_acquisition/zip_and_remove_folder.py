#!/usr/bin/env python3
# -*- coding:utf-8 -*-
######
# -----
# Copyright (c) 2023 FIT-Project
# SPDX-License-Identifier: GPL-3.0-only
# -----
######

import os
import shutil

from fit_common.gui.utils import Status

from fit_acquisition.tasks.task import Task
from fit_acquisition.tasks.task_worker import TaskWorker


class ZipAndRemoveFolderWorker(TaskWorker):
    def start(self):
        self.started.emit()
        shutil.make_archive(
            self.options["acquisition_content_directory"],
            "zip",
            self.options["acquisition_content_directory"],
        )

        has_files_downloads_folder = []

        downloads_folder = os.path.join(self.options["acquisition_directory"], "downloads")
        if os.path.isdir(downloads_folder):
            has_files_downloads_folder = os.listdir(downloads_folder)

        if len(has_files_downloads_folder) > 0:
            shutil.make_archive(downloads_folder, "zip", downloads_folder)
        try:
            shutil.rmtree(self.options["acquisition_content_directory"])
            if os.path.isdir(downloads_folder):
                shutil.rmtree(downloads_folder)
            self.finished.emit()

        except OSError as e:
            self.error.emit(
                {
                    "title": self.translations["ZIP_AND_REMOVE_FOLDER"],
                    "message": self.translations["DELETE_FOLDER_ERROR"],
                    "details": "Error: %s - %s." % (e.filename, e.strerror),
                }
            )


class TaskZipAndRemoveFolder(Task):
    def __init__(self, logger, progress_bar=None, status_bar=None):
        super().__init__(
            logger,
            progress_bar,
            status_bar,
            label="ZIP_AND_REMOVE_FOLDER",
            worker_class=ZipAndRemoveFolderWorker,
        )

    def start(self):
        super().start_task(self.translations["ZIP_AND_REMOVE_FOLDER_STARTED"])


    def _finished(self, status=Status.SUCCESS, details=""):
        message = self.translations["ZIP_AND_REMOVE_FOLDER_COMPLETED"].format(
                status.name
        )

        super()._finished(status, details, message)
