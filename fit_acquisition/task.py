#!/usr/bin/env python3
# -*- coding:utf-8 -*-
######
# -----
# Copyright (c) 2023 FIT-Project
# SPDX-License-Identifier: GPL-3.0-only
# -----
######

from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QStatusBar, QLabel

from fit_common.gui.utils import Status, State

from fit_acquisition.tasks_handler import TasksHandler
from fit_acquisition.lang import load_translations


class Task(QObject):
    started = Signal()
    finished = Signal()

    def __init__(self, logger, progress_bar, status_bar):
        super().__init__()

        self.is_infinite_loop = False

        self.logger = logger
        self.progress_bar = progress_bar
        self.status_bar = status_bar

        self.state = State.INITIALIZATED
        self.status = Status.SUCCESS
        self.details = ""
        self.task_handler = TasksHandler()
        self.task_handler.add_task(self)
        self.__increment = 0

        self.__translations = load_translations()

    @property
    def label(self):
        return self.__label

    @label.setter
    def label(self, label):
        self.__label = label

    @property
    def options(self):
        return self._options

    @options.setter
    def options(self, options):
        self._options = options

    @property
    def state(self):
        return self.__state

    @state.setter
    def state(self, state):
        self.__state = state

    @property
    def status(self):
        return self.__status

    @status.setter
    def status(self, status):
        self.__status = status

    @property
    def details(self):
        return self.__details

    @details.setter
    def details(self, details):
        self.__details = details

    @property
    def increment(self):
        return self.__increment

    @increment.setter
    def increment(self, increment):
        self.__increment = increment

    @property
    def sub_tasks(self):
        return self.__sub_tasks

    @property
    def is_infinite_loop(self):
        return self.__is_infinite_loop

    @is_infinite_loop.setter
    def is_infinite_loop(self, is_infinite_loop):
        self.__is_infinite_loop = is_infinite_loop

    @sub_tasks.setter
    def sub_tasks(self, sub_tasks):
        self.__sub_tasks = sub_tasks

    @property
    def translations(self):
        return self.__translations

    def update_progress_bar(self):
        if self.progress_bar is not None:
            self.progress_bar.setValue(self.progress_bar.value() + int(self.increment))

    def set_message_on_the_statusbar(self, message):
        if self.status_bar is not None:
            if isinstance(self.status_bar, QStatusBar):
                self.status_bar.showMessage(message)
            elif isinstance(self.status_bar, QLabel):
                self.status_bar.setText(message)

    def update_task(self, state, status, details=""):
        self.state = state
        self.status = status
        self.details = details
