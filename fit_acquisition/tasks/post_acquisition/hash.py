#!/usr/bin/env python3
# -*- coding:utf-8 -*-
######
# -----
# Copyright (c) 2023 FIT-Project
# SPDX-License-Identifier: GPL-3.0-only
# -----
######

import hashlib
import logging
import os

from fit_common.gui.utils import Status

from fit_acquisition.tasks.task import Task
from fit_acquisition.tasks.task_worker import TaskWorker


class HashWorker(TaskWorker):
    logger = logging.getLogger("hashreport")

    def __calculate_hash(self, filename, algorithm):
        with open(filename, "rb") as f:
            file_hash = hashlib.new(algorithm)
            while chunk := f.read(8192):
                file_hash.update(chunk)

            return file_hash.hexdigest()

    def start(self):
        self.started.emit()

        files = [
            f.name
            for f in os.scandir(self.options["acquisition_directory"])
            if f.is_file()
        ]
        self.options["exclude_list"].append("acquisition.hash")
        self.options["exclude_list"].append("acquisition.log")
        for file in files:
            if file not in self.options["exclude_list"]:
                filename = os.path.join(self.options["acquisition_directory"], file)
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
    def __init__(self, logger, progress_bar=None, status_bar=None):
        super().__init__(
            logger,
            progress_bar,
            status_bar,
            label="HASHFILE",
            worker_class=HashWorker,
        )

    @Task.options.getter
    def options(self):
        return self._options

    @options.setter
    def options(self, options):
        options["exclude_list"] = list()
        if "exclude_from_hash_calculation" in options and isinstance(
            options["exclude_from_hash_calculation"], list
        ):
            options["exclude_list"] = options["exclude_from_hash_calculation"]

        self._options = options

    def start(self):
        super().start_task(self.translations["CALCULATE_HASHFILE_STARTED"])

    def _finished(self, status=Status.SUCCESS, details=""):
        message = self.translations["CALCULATE_HASHFILE_COMPLETED"].format(status.name)

        super()._finished(status, details, message)
