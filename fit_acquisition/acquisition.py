#!/usr/bin/env python3
# -*- coding:utf-8 -*-
######
# -----
# Copyright (c) 2023 FIT-Project
# SPDX-License-Identifier: GPL-3.0-only
# -----
######

import logging.config
from shiboken6 import isValid

from PySide6.QtCore import QObject, Signal

from fit_acquisition.post import PostAcquisition
from fit_acquisition.logger import LogConfigTools

from fit_acquisition.tasks_manager import TasksManager
from fit_acquisition.class_names import *
from fit_configurations.controller.tabs.network.networkcheck import (
    NetworkControllerCheck,
)

from fit_common.core.utils import get_ntp_date_and_time
from fit_common.gui.utils import State


from fit_acquisition.lang import load_translations

from enum import Enum


import fit_acquisition.tasks.infinite_loop
import fit_acquisition.tasks.nettools
import fit_acquisition.tasks.post_acquisition
import fit_acquisition.tasks.post_acquisition.pec
import fit_acquisition.tasks.post_acquisition.report


class AcquisitionStatus(Enum):
    UNSTARTED = 1
    STARTED = 2
    STOPED = 3


class Acquisition(QObject):
    post_acquisition_is_finished = Signal()
    start_tasks_is_finished = Signal()
    stop_tasks_is_finished = Signal()

    def __init__(
        self,
        logger,
        parent=None,
        packages=[],
    ):
        super().__init__(parent)

        self.logger = logger
        self.__options = None
        self.__progress_bar = None
        self.__status_bar = None
        

        self.translations = load_translations()

        self.tasks_manager = TasksManager(parent)

        core_task_packages =[
            fit_acquisition.tasks.infinite_loop,
            fit_acquisition.tasks.nettools,
            fit_acquisition.tasks.post_acquisition,
            fit_acquisition.tasks.post_acquisition.pec,
            fit_acquisition.tasks.post_acquisition.report,
        ]

        packages += core_task_packages

        for package in packages:
            self.tasks_manager.register_task_package(package)

        self.tasks_manager.load_all_task_modules()

        self.start_tasks = list()
        self.stop_tasks = list()
        self.post_tasks = [
            ZIP_AND_REMOVE_FOLDER,
            SAVE_CASE_INFO,
            HASH,
            REPORT,
            TIMESTAMP,
            PEC_AND_DOWNLOAD_EML,
        ]

        self.post_acquisition = PostAcquisition(self.parent())
        self.post_acquisition.finished.connect(self.post_acquisition_is_finished.emit)
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

    def load_tasks(self):
        self.log_confing = LogConfigTools()

        if self.logger.name == "view.scrapers.web.web":
            self.log_confing.set_dynamic_loggers()

        self.log_confing.change_filehandlers_path(self.options["acquisition_directory"])
        logging.config.dictConfig(self.log_confing.config)

        __all_tasks = self.start_tasks + self.stop_tasks + self.post_tasks

        self.tasks_manager.init_tasks(
            __all_tasks, self.logger, self.__progress_bar, self.__status_bar
        )

    def unload_tasks(self):
        for task in self.tasks_manager.get_tasks():
            if isValid(task):
                task.deleteLater()
        self.tasks_manager.clear_tasks()

    def start(self):
        self.log_start_message()

        tasks = self.tasks_manager.get_tasks_from_class_name(self.start_tasks)

        if len(tasks) == 0:
            self.start_tasks_is_finished.emit()
        else:
            for task in tasks:
                task.started.connect(self.__started_task_handler)
                task.options = self.options
                task.increment = self.calculate_increment()
                task.start()

    def __started_task_handler(self):
        if self.tasks_manager.are_task_names_in_the_same_state(
            self.start_tasks, State.STARTED
        ):
            self.start_tasks_is_finished.emit()

    def stop(self):
        self.log_stop_message()
        tasks = self.tasks_manager.get_tasks_from_class_name(self.stop_tasks)

        if len(tasks) == 0:
            self.stop_tasks_is_finished.emit()
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
        if self.tasks_manager.are_task_names_in_the_same_state(
            self.stop_tasks, State.COMPLETED
        ):
            self.stop_tasks_is_finished.emit()

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
            NetworkControllerCheck().configuration["ntp_server"]
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
