#!/usr/bin/env python3
# -*- coding:utf-8 -*-
######
# -----
# Copyright (c) 2023 FIT-Project
# SPDX-License-Identifier: GPL-3.0-only
# -----
######

import shutil
import os

from shiboken6 import isValid

from PySide6 import QtWidgets
from PySide6.QtCore import QObject, Signal, QThread, QEventLoop, QTimer


from fit_acquisition.task import Task
from fit_common.gui.utils import State, Status
from fit_acquisition.lang import load_translations
from fit_common.gui.error import Error as ErrorView


class ZipAndRemoveFolderWorker(QObject):
    finished = Signal()
    started = Signal()
    error = Signal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.translations = load_translations()

    def set_options(self, options):
        self.acquisition_content_directory = options["acquisition_content_directory"]
        self.acquisition_directory = options["acquisition_directory"]

    def start(self):
        self.started.emit()
        shutil.make_archive(
            self.acquisition_content_directory,
            "zip",
            self.acquisition_content_directory,
        )

        has_files_downloads_folder = []

        downloads_folder = os.path.join(self.acquisition_directory, "downloads")
        if os.path.isdir(downloads_folder):
            has_files_downloads_folder = os.listdir(downloads_folder)

        if len(has_files_downloads_folder) > 0:
            shutil.make_archive(downloads_folder, "zip", downloads_folder)
        try:
            shutil.rmtree(self.acquisition_content_directory)
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
    def __init__(self, logger, progress_bar=None, status_bar=None, parent=None):
        super().__init__(logger, progress_bar, status_bar, parent)

        self.translations = load_translations()

        self.label = self.translations["ZIP_AND_REMOVE_FOLDER"]

        self.worker_thread = QThread()
        self.worker = ZipAndRemoveFolderWorker()
        self.worker.moveToThread(self.worker_thread)
        self.worker_thread.started.connect(self.worker.start)
        self.worker.started.connect(self.__started)
        self.worker.finished.connect(self.__finished)
        self.worker.error.connect(self.__handle_error)

        self.destroyed.connect(lambda: self.__destroyed_handler(self.__dict__))

    def __handle_error(self, error):
        error_dlg = ErrorView(
            QtWidgets.QMessageBox.Icon.Critical,
            error.get("title"),
            error.get("message"),
            error.get("details"),
        )
        error_dlg.exec()
        self.__finished(Status.FAIL)

    def start(self):
        self.worker.set_options(self.options)
        self.update_task(State.STARTED, Status.PENDING)
        self.set_message_on_the_statusbar(
            self.translations["ZIP_AND_REMOVE_FOLDER_STARTED"].format(
                self.options.get("acquisition_content_directory")
            )
        )
        self.worker_thread.start()

    def __started(self):
        self.update_task(State.STARTED, Status.SUCCESS)
        self.started.emit()

    def __finished(self, status=Status.SUCCESS):
        self.logger.info(self.translations["ZIP_AND_REMOVE_FOLDER"])
        self.set_message_on_the_statusbar(
            self.translations["ZIP_AND_REMOVE_FOLDER_COMPLETED"].format(
                self.options.get("acquisition_content_directory")
            )
        )
        self.update_progress_bar()

        self.update_task(State.COMPLETED, status)

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
