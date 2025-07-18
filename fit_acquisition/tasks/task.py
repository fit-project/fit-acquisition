#!/usr/bin/env python3
# -*- coding:utf-8 -*-
######
# -----
# Copyright (c) 2023 FIT-Project
# SPDX-License-Identifier: GPL-3.0-only
# -----
######

from datetime import datetime, timedelta

from fit_common.gui.utils import State, Status
from PySide6.QtCore import QEventLoop, QObject, QThread, QTimer, Signal
from PySide6.QtWidgets import QLabel, QStatusBar
from shiboken6 import isValid

from fit_acquisition.lang import load_translations
from fit_acquisition.tasks.tasks_handler import TasksHandler


class Task(QObject):
    started = Signal()
    finished = Signal()
    __is_task__ = True

    def __init__(
        self,
        logger,
        progress_bar,
        status_bar,
        *,
        label=None,
        is_infinite_loop=False,
        worker_class=None,
    ):
        super().__init__()

        self.logger = logger
        self.progress_bar = progress_bar
        self.status_bar = status_bar

        self.__start_time = None
        self.__end_time = None

        self.state = State.INITIALIZATED
        self.status = Status.SUCCESS
        self.details = ""
        self.__increment = 0

        self.__translations = load_translations()
        self.label = self.__translations.get(label, label) if label else ""
        self.is_infinite_loop = is_infinite_loop

        self.task_handler = TasksHandler()
        self.task_handler.add_task(self)

        if worker_class:
            self.worker_thread = QThread()
            self.worker = worker_class()
            self.worker.moveToThread(self.worker_thread)
            self.worker_thread.started.connect(self.worker.start)

            self.worker.started.connect(self._started)
            self.worker.finished.connect(self._finished)
            self.worker.error.connect(self._handle_error)

        self.destroyed.connect(lambda: self._destroyed_handler(self.__dict__))

    def is_active(self):
        return self.state != State.COMPLETED

    def get_elapsed_time(self) -> timedelta:
        if self.__start_time and not self.__end_time:
            return datetime.now() - self.__start_time
        return timedelta(0)

    def get_status_summary(self):
        if self.is_active():
            return f"{self.label} in esecuzione da {self.get_elapsed_time().seconds} secondi"
        elif self.state == State.COMPLETED:
            return f"{self.label} completato con stato {self.status.name}"
        else:
            return f"{self.label} ({self.state.name})"

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

    @sub_tasks.setter
    def sub_tasks(self, sub_tasks):
        self.__sub_tasks = sub_tasks

    @property
    def is_infinite_loop(self):
        return self.__is_infinite_loop

    @is_infinite_loop.setter
    def is_infinite_loop(self, value):
        self.__is_infinite_loop = value

    @property
    def translations(self):
        return self.__translations

    def start_task(self, message):
        self.update_task(State.STARTED, Status.PENDING)
        self.set_message_on_the_statusbar(message)

        self.worker.options = self.options
        self.worker_thread.start()

    def stop_task(self, message):
        self.update_task(State.STOPPED, Status.PENDING)
        self.set_message_on_the_statusbar(message)
        self.worker.stop()

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

    def _started(self, details=""):
        self.__start_time = datetime.now()  # ⏱️ avvio
        self.__end_time = None
        self.update_task(State.STARTED, Status.SUCCESS, details)
        self.started.emit()

    def _finished(self, status=Status.SUCCESS, details="", message=""):
        self.__end_time = datetime.now()  # ⏱️ fine
        self.logger.info(message)
        self.set_message_on_the_statusbar(message)
        self.update_progress_bar()
        self.update_task(State.COMPLETED, status, details)
        self.finished.emit()

        if hasattr(self, "worker_thread"):
            loop = QEventLoop()
            QTimer.singleShot(1000, loop.quit)
            loop.exec()
            self.worker_thread.quit()
            self.worker_thread.wait()

    def _handle_error(self, error):
        self._finished(Status.FAILURE, error.get("details"))

    def _destroyed_handler(self, _dict):
        if hasattr(self, "worker_thread") and isValid(self.worker_thread):
            if self.worker_thread.isRunning():
                self.worker_thread.quit()
                self.worker_thread.wait()
