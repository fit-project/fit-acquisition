#!/usr/bin/env python3
# -*- coding:utf-8 -*-
######
# -----
# Copyright (c) 2023 FIT-Project
# SPDX-License-Identifier: GPL-3.0-only
# -----
######

import logging
import os
import hashlib
from shiboken6 import isValid


from PySide6.QtCore import QObject, Signal, QThread, QEventLoop, QTimer


from fit_acquisition.task import Task
from fit_common.gui.utils import State, Status
from fit_acquisition.lang import load_translations


class HashWorker(QObject):
    logger = logging.getLogger("hashreport")
    finished = Signal()
    started = Signal()

    @property
    def folder(self):
        return self._folder

    @folder.setter
    def folder(self, folder):
        self._folder = folder

    @property
    def exclude_list(self):
        return self._exclude_list

    @exclude_list.setter
    def exclude_list(self, exclude_list):
        self._exclude_list = exclude_list

    def __calculate_hash(self, filename, algorithm):
        with open(filename, "rb") as f:
            file_hash = hashlib.new(algorithm)
            while chunk := f.read(8192):
                file_hash.update(chunk)

            return file_hash.hexdigest()

    def start(self):
        self.started.emit()

        files = [f.name for f in os.scandir(self.folder) if f.is_file()]
        list().append
        self.exclude_list.append("acquisition.hash")
        self.exclude_list.append("acquisition.log")
        self.exclude_list.append("acquisition_video.mp4")
        for file in files:
            if file not in self.exclude_list:
                filename = os.path.join(self.folder, file)
                file_stats = os.stat(filename)
                self.logger.info(
                    "========================================================="
                )
                self.logger.info(f"Name: {file}")
                self.logger.info(f"Size: {file_stats.st_size}")
                algorithm = "md5"
                self.logger.info(f"MD5: {self.__calculate_hash(filename, algorithm)}")
                algorithm = "sha1"
                self.logger.info(f"SHA-1: {self.__calculate_hash(filename, algorithm)}")
                algorithm = "sha256"
                self.logger.info(
                    f"SHA-256: {self.__calculate_hash(filename, algorithm)}"
                )

        self.finished.emit()


class TaskHash(Task):
    def __init__(self, logger, progress_bar=None, status_bar=None, parent=None):
        super().__init__(logger, progress_bar, status_bar, parent)

        self.translations = load_translations()

        self.label = self.translations["HASHFILE"]

        self.worker_thread = QThread()
        self.worker = HashWorker()
        self.worker.moveToThread(self.worker_thread)
        self.worker_thread.started.connect(self.worker.start)
        self.worker.started.connect(self.__started)
        self.worker.finished.connect(self.__finished)

        self.destroyed.connect(lambda: self.__destroyed_handler(self.__dict__))

    def start(self):
        self.update_task(State.STARTED, Status.PENDING)
        self.set_message_on_the_statusbar(
            self.translations["CALCULATE_HASHFILE_STARTED"]
        )
        self.worker.folder = self.options["acquisition_directory"]
        self.worker.exclude_list = list()
        if "exclude_from_hash_calculation" in self.options:
            self.worker.exclude_list = self.options["exclude_from_hash_calculation"]

        self.worker_thread.start()

    def __started(self):
        self.update_task(State.STARTED, Status.SUCCESS)
        self.started.emit()

    def __finished(self):
        self.logger.info(self.translations["CALCULATE_HASHFILE"])
        self.set_message_on_the_statusbar(
            self.translations["CALCULATE_HASHFILE_COMPLETED"]
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
