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
        self.task_handler = TasksHandler()
        self._pending_tasks = set()
        self.__init_ui()
        self.__connect_task_signals()
        self.translations = load_translations()

    def __init_ui(self):
        self.setWindowFlags(QtCore.Qt.WindowType.FramelessWindowHint)
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_TranslucentBackground)

        self.ui = Ui_tasks_info()
        self.ui.setupUi(self)

        if self.parent():
            self.setGeometry(self.parent().geometry())

        self.ui.task_log_text.setReadOnly(True)
        self.ui.task_log_text.clear()

    def __connect_task_signals(self):
        tasks = self.task_handler.get_tasks()
        for task in tasks:
            self._pending_tasks.add(task.label)
            task.started.connect(lambda t=task: self.log_task_event(t, "started"))
            task.finished.connect(lambda t=task: self._on_task_finished(t))

    def _on_task_finished(self, task):
        if task.status == Status.FAILURE:
            self.log_task_event(task, "error", task.details)
        else:
            self.log_task_event(task, "finished")
            self._pending_tasks.discard(task.label)
            if not self._pending_tasks:
                QtCore.QTimer.singleShot(500, self.close)

    def log_task_event(self, task, event, extra=""):
        now = datetime.now().strftime("%H:%M:%S")
        symbol = {"started": "▶️", "finished": "✅", "error": "❌"}.get(event, "ℹ️")
        status = f" [{task.status.name}]" if event == "finished" else ""
        line = f"{symbol} {now} - {task.label} {event}{status} {extra}".strip()
        self.ui.task_log_text.append(line)
