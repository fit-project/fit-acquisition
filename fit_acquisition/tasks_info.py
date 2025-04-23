#!/usr/bin/env python3
# -*- coding:utf-8 -*-
######
# -----
# Copyright (c) 2023 FIT-Project
# SPDX-License-Identifier: GPL-3.0-only
# -----
######

from PySide6 import QtCore, QtGui, QtWidgets

from importlib.resources import files

from fit_common.core.utils import get_version
from fit_acquisition.tasks_handler import TasksHandler


from fit_acquisition.task_info_ui import (
    Ui_acquisition_dialog_info,
)

from fit_assets import resources


class TasksInfo(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super(TasksInfo, self).__init__(parent)
        self.task_handler = TasksHandler()
        self.__init_ui()

    def __init_ui(self):
        # HIDE STANDARD TITLE BAR
        self.setWindowFlags(QtCore.Qt.WindowType.FramelessWindowHint)
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_TranslucentBackground)

        self.ui = Ui_acquisition_dialog_info()
        self.ui.setupUi(self)

        # CUSTOM TOP BAR
        self.ui.left_box.mouseMoveEvent = self.move_window

        # MINIMIZE BUTTON
        self.ui.minimize_button.clicked.connect(self.showMinimized)

        # CLOSE BUTTON
        self.ui.close_button.clicked.connect(self.close)

        # SET VERSION
        self.ui.version.setText(get_version())

        icon_path = files("fit_assets.icons").joinpath("info-circle.png")

        self.icon = QtGui.QIcon(str(icon_path))

        self.ui.acquisition_table_info.setColumnCount(3)
        self.ui.acquisition_table_info.setColumnWidth(0, 250)

        # Set the table headers
        self.ui.acquisition_table_info.setHorizontalHeaderLabels(
            ["Task", "State", "Status"]
        )
        self.ui.acquisition_table_info.horizontalHeader().setStretchLastSection(True)
        self.__load_current_tasks()

    def mousePressEvent(self, event):
        self.dragPos = event.globalPosition().toPoint()

    def move_window(self, event):
        if event.buttons() == QtCore.Qt.MouseButton.LeftButton:
            self.move(self.pos() + event.globalPosition().toPoint() - self.dragPos)
            self.dragPos = event.globalPosition().toPoint()
            event.accept()

    def __load_current_tasks(self):
        for task in self.task_handler.get_tasks():
            row = self.ui.acquisition_table_info.rowCount()
            self.ui.acquisition_table_info.insertRow(row)
            status = QtWidgets.QTableWidgetItem(task.status)

            if task.details:
                status.setIcon(self.icon)
                status.setToolTip(task.details)

            self.ui.acquisition_table_info.setItem(
                row, 0, QtWidgets.QTableWidgetItem(task.label)
            )
            self.ui.acquisition_table_info.setItem(
                row, 1, QtWidgets.QTableWidgetItem(task.state)
            )
            self.ui.acquisition_table_info.setItem(row, 2, status)

        if self.task_handler.get_tasks():
            for column in range(self.ui.acquisition_table_info.columnCount()):
                item = self.ui.acquisition_table_info.item(row, column)
                if item is not None:
                    item.setFlags(
                        QtCore.Qt.ItemFlag.ItemIsEnabled
                        | QtCore.Qt.ItemFlag.ItemIsSelectable
                    )
