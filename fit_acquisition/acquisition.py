#!/usr/bin/env python3
# -*- coding:utf-8 -*-
######
# -----
# Copyright (c) 2023 FIT-Project
# SPDX-License-Identifier: GPL-3.0-only
# -----
######

import logging.config
from enum import Enum, auto

from fit_common.core.utils import get_ntp_date_and_time
from fit_common.gui.utils import State
from fit_configurations.controller.tabs.network.network_check import (
    NetworkCheckController,
)
from PySide6.QtCore import QObject, Signal
from shiboken6 import isValid

from fit_acquisition.class_names import class_names
from fit_acquisition.lang import load_translations
from fit_acquisition.logger import LogConfigTools
from fit_acquisition.post import PostAcquisition
from fit_acquisition.tasks.tasks_manager import TasksManager


class AcquisitionStatus(Enum):
    UNSTARTED = auto()
    STARTED = auto()
    STOPPED = auto()
    FINISHED = auto()

    def __str__(self):
        return self.name.capitalize()


class Acquisition(QObject):
    post_acquisition_finished = Signal()
    start_tasks_finished = Signal()
    stop_tasks_finished = Signal()

    def __init__(
        self,
        logger,
        packages=[],
    ):
        super().__init__()

        self.logger = logger
        self.__options = None
        self.__progress_bar = None
        self.__status_bar = None

        self.translations = load_translations()

        self.tasks_manager = TasksManager()

        core_task_packages = [
            "fit_acquisition.tasks.infinite_loop",
            "fit_acquisition.tasks.network_tools",
            "fit_acquisition.tasks.post_acquisition",
        ]

        packages += core_task_packages

        for package in packages:
            self.tasks_manager.register_task_package(package)

        self.tasks_manager.load_all_task_modules()

        self.start_tasks = list()
        self._start_emitted = False

        self.stop_tasks = list()
        self._stop_emitted = False

        self.__post_tasks = (
            class_names.ZIP_AND_REMOVE_FOLDER,
            class_names.SAVE_CASE_INFO,
            class_names.HASH,
            class_names.REPORT,
            class_names.TIMESTAMP,
            class_names.PEC_AND_DOWNLOAD_EML,
        )

        self.post_acquisition = PostAcquisition()
        self.post_acquisition.finished.connect(self.post_acquisition_finished.emit)
        self.destroyed.connect(lambda: self.__destroyed_handler(self.__dict__))

    @property
    def options(self):
        return self.__options

    @options.setter
    def options(self, value):
        self.__options = value

    @property
    def progress_bar(self):
        return self.__progress_bar

    @progress_bar.setter
    def progress_bar(self, value):
        self.__progress_bar = value

    @property
    def status_bar(self):
        return self.__status_bar

    @status_bar.setter
    def status_bar(self, value):
        self.__status_bar = value

    @property
    def status_bar_visible(self) -> bool:
        return self.__status_bar.isVisible() if self.__status_bar else False

    @status_bar_visible.setter
    def status_bar_visible(self, visible: bool):
        if self.__status_bar:
            self.__status_bar.setVisible(visible)

    @property
    def progress_bar_visible(self) -> bool:
        return self.__progress_bar.isVisible() if self.__progress_bar else False

    @progress_bar_visible.setter
    def progress_bar_visible(self, visible: bool):
        if self.__progress_bar:
            self.__progress_bar.setVisible(visible)

    @property
    def reset_status_bar(self):
        if self.__status_bar:
            self.__status_bar.setText("")

    @property
    def reset_progress_bar(self):
        if self.__progress_bar:
            self.__progress_bar.setValue(0)

    @property
    def progress(self) -> int:
        return self.__progress_bar.value() if self.__progress_bar else 0

    @progress.setter
    def progress(self, value: int):
        if self.__progress_bar:
            self.__progress_bar.setValue(value)

    def load_tasks(self):
        self.log_confing = LogConfigTools()

        if self.logger.name == "view.scrapers.web.web":
            self.log_confing.set_dynamic_loggers()

        self.log_confing.change_filehandlers_path(self.options["acquisition_directory"])
        logging.config.dictConfig(self.log_confing.config)

        all_tasks = self.start_tasks + self.stop_tasks + list(self.__post_tasks)

        self.tasks_manager.init_tasks(
            all_tasks, self.logger, self.__progress_bar, self.__status_bar
        )

    def unload_tasks(self):
        for task in self.tasks_manager.get_tasks():
            if isValid(task):
                task.deleteLater()
        self.tasks_manager.clear_tasks()

    def run_start_tasks(self):
        tasks = self.tasks_manager.get_tasks_from_class_name(self.start_tasks)

        if len(tasks) == 0:
            self.start_tasks_finished.emit()
        else:
            for task in tasks:
                task.started.connect(self.__started_task_handler)
                task.options = self.options
                task.increment = self.calculate_increment()
                task.start()

    def __started_task_handler(self):
        if (
            not self._start_emitted
            and self.tasks_manager.are_task_names_in_the_same_state(
                self.start_tasks, State.STARTED
            )
        ):
            self._start_emitted = True
            self.start_tasks_finished.emit()

    def run_stop_tasks(self):
        tasks = self.tasks_manager.get_tasks_from_class_name(self.stop_tasks)

        if len(tasks) == 0:
            self.stop_tasks_finished.emit()
        else:
            for task in tasks:
                task.finished.connect(self.__finished_task_handler)
                task.options = self.options
                task.increment = self.calculate_increment()

                if task.is_infinite_loop:
                    task.stop()
                else:
                    task.start()

    def __finished_task_handler(self):
        if (
            not self._stop_emitted
            and self.tasks_manager.are_task_names_in_the_same_state(
                self.stop_tasks, State.COMPLETED
            )
        ):
            self._stop_emitted = True
            self.stop_tasks_finished.emit()

    def start_post_acquisition(self):
        self.post_acquisition.start_post_acquisition_sequence(
            self.calculate_increment(), self.options
        )

    def log_start_message(self):
        self.logger.info(self.translations["ACQUISITION_STARTED"])
        self.logger.info(
            self.translations["NTP_ACQUISITION_TIME"].format("start", self.get_time())
        )

    def log_stop_message(self):
        self.logger.info(self.translations["ACQUISITION_STOPPED"])
        self.logger.info(
            self.translations["NTP_ACQUISITION_TIME"].format("stop", self.get_time())
        )

    def log_end_message(self):
        self.logger.info(self.translations["ACQUISITION_FINISHED"])
        self.logger.info(
            self.translations["NTP_ACQUISITION_TIME"].format("stop", self.get_time())
        )

    def get_time(self):
        return get_ntp_date_and_time(
            NetworkCheckController().configuration["ntp_server"]
        )

    def calculate_increment(self):
        return 100 / len(self.tasks_manager.get_tasks())

    def set_completed_progress_bar(self):
        if self.__progress_bar is not None:
            self.__progress_bar.setValue(
                self.__progress_bar.value() + (100 - self.__progress_bar.value())
            )

    def __destroyed_handler(self, __dict):
        self.unload_tasks()
