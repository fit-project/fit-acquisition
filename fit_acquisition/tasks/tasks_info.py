#!/usr/bin/env python3
# -*- coding:utf-8 -*-
######
# -----
# Copyright (c) 2023 FIT-Project
# SPDX-License-Identifier: GPL-3.0-only
# -----
######

from datetime import datetime

from fit_common.gui.utils import Status
from PySide6 import QtCore, QtWidgets

from fit_acquisition.lang import load_translations
from fit_acquisition.tasks.tasks_handler import TasksHandler
from fit_acquisition.tasks.tasks_info_ui import Ui_tasks_info


class TasksInfo(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super(TasksInfo, self).__init__(parent)
        self.__task_handler = TasksHandler()
        self.__pending_tasks = set()
        self.__init_ui()
        self.__connect_task_signals()
        self.__translations = load_translations()

        self.__active_tasks_timer = QtCore.QTimer(self)
        self.__active_tasks_timer.timeout.connect(self.__update_active_tasks_status)
        self.__active_tasks_timer.start(1000)

    def __init_ui(self):
        self.setWindowFlags(QtCore.Qt.WindowType.FramelessWindowHint)
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_TranslucentBackground)

        self.ui = Ui_tasks_info()
        self.ui.setupUi(self)

        self.active_tasks_label = QtWidgets.QLabel()
        self.active_tasks_label.setStyleSheet("color: lightgreen; font-weight: bold;")
        self.ui.content_box_layout.insertWidget(0, self.active_tasks_label)

        if self.parent():
            self.setGeometry(self.parent().geometry())

        self.ui.task_log_text.setReadOnly(True)
        self.ui.task_log_text.clear()

    def __update_active_tasks_status(self):
        active_tasks = [
            task
            for task in self.__task_handler.get_tasks()
            if hasattr(task, "is_active") and task.is_active()
        ]

        if active_tasks:
            lines = [
                f"🟡 {task.label} ({task.get_elapsed_time().seconds}s)"
                for task in active_tasks
            ]
            text = self.__translations["ACTIVE_TASKS_HEADER"] + "\n".join(lines)
        else:
            text = self.__translations["NO_ACTIVE_TASKS"]

        self.active_tasks_label.setText(text)

    def __connect_task_signals(self):
        tasks = self.__task_handler.get_tasks()
        for task in tasks:
            self.__pending_tasks.add(task.label)
            task.started.connect(lambda t=task: self.__log_task_event(t, "started"))
            task.finished.connect(lambda t=task: self.__on_task_finished(t))

    def __on_task_finished(self, task):
        if task.status == Status.FAILURE:
            self.__log_task_event(task, "error", task.details)
        else:
            self.__log_task_event(task, "finished")
            self.__pending_tasks.discard(task.label)
            if not self.__pending_tasks:
                QtCore.QTimer.singleShot(500, self.close)

    def __log_task_event(self, task, event, extra=""):
        now = datetime.now().strftime("%H:%M:%S")
        symbol = {"started": "▶️", "finished": "✅", "error": "❌"}.get(event, "ℹ️")
        status = f" [{task.status.name}]" if event == "finished" else ""
        line = f"{symbol} {now} - {task.label} {event}{status} {extra}".strip()
        self.ui.task_log_text.append(line)
