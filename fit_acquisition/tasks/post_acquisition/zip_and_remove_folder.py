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

from fit_common.core import debug, get_context
from fit_common.gui.utils import Status

from fit_acquisition.tasks.task import Task
from fit_acquisition.tasks.task_worker import TaskWorker


class ZipAndRemoveFolderWorker(TaskWorker):
    def start(self):
        debug("ℹ️ ZipAndRemoveFolderWorker.start: begin", context=get_context(self))
        self.started.emit()

        acquisition_content_directory = None
        if self.options.get("type") != "web":
            acquisition_content_directory = self.options.get(
                "acquisition_content_directory"
            )
            if not acquisition_content_directory or not os.path.isdir(
                acquisition_content_directory
            ):
                debug(
                    f"⚠️ acquisition_content_directory missing: {acquisition_content_directory}",
                    context=get_context(self),
                )
            else:
                debug(
                    f"ℹ️ zipping acquisition_content_directory={acquisition_content_directory}",
                    context=get_context(self),
                )
                try:
                    shutil.make_archive(
                        acquisition_content_directory,
                        "zip",
                        acquisition_content_directory,
                    )
                except (OSError, shutil.Error) as exc:
                    debug(
                        f"❌ zip acquisition_content_directory failed: {exc}",
                        context=get_context(self),
                    )
                    self.error.emit(
                        {
                            "title": self.translations["ZIP_AND_REMOVE_FOLDER"],
                            "message": self.translations["ZIP_AND_REMOVE_FOLDER_ERROR"],
                            "details": str(exc),
                        }
                    )
                    return
                debug("✅ zipped acquisition_content_directory", context=get_context(self))

        has_files_downloads_folder = []

        downloads_folder = os.path.join(self.options["acquisition_directory"], "downloads")
        debug(
            f"ℹ️ downloads_folder={downloads_folder} exists={os.path.isdir(downloads_folder)}",
            context=get_context(self),
        )
        if os.path.isdir(downloads_folder):
            has_files_downloads_folder = os.listdir(downloads_folder)
            debug(
                f"ℹ️ downloads_folder file_count={len(has_files_downloads_folder)}",
                context=get_context(self),
            )

        if len(has_files_downloads_folder) > 0:
            debug(
                f"ℹ️ zipping downloads_folder={downloads_folder}",
                context=get_context(self),
            )
            try:
                shutil.make_archive(downloads_folder, "zip", downloads_folder)
            except (OSError, shutil.Error) as exc:
                debug(
                    f"❌ zip downloads_folder failed: {exc}",
                    context=get_context(self),
                )
                self.error.emit(
                    {
                        "title": self.translations["ZIP_AND_REMOVE_FOLDER"],
                        "message": self.translations["ZIP_AND_REMOVE_FOLDER_ERROR"],
                        "details": str(exc),
                    }
                )
                return
            debug("✅ zipped downloads_folder", context=get_context(self))
        try:
            if acquisition_content_directory and os.path.isdir(
                acquisition_content_directory
            ):
                debug(
                    f"ℹ️ removing acquisition_content_directory={acquisition_content_directory}",
                    context=get_context(self),
                )
                shutil.rmtree(acquisition_content_directory)
                debug(
                    "✅ removed acquisition_content_directory",
                    context=get_context(self),
                )
            if os.path.isdir(downloads_folder):
                debug(
                    f"ℹ️ removing downloads_folder={downloads_folder}",
                    context=get_context(self),
                )
                shutil.rmtree(downloads_folder)
                debug("✅ removed downloads_folder", context=get_context(self))
            self.finished.emit()
            debug("✅ ZipAndRemoveFolderWorker.start: done", context=get_context(self))

        except OSError as e:
            debug(
                f"❌ ZipAndRemoveFolderWorker.start: rmtree error {e.filename} - {e.strerror}",
                context=get_context(self),
            )
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
