#!/usr/bin/env python3
# -*- coding:utf-8 -*-
######
# -----
# Copyright (c) 2023 FIT-Project
# SPDX-License-Identifier: GPL-3.0-only
# -----
######


import os
import sys
import unittest
import logging

from PySide6 import QtWidgets
from PySide6.QtWidgets import QApplication
from PySide6.QtTest import QSignalSpy

from fit_common.gui.utils import State, Status
from fit_common.core.utils import resolve_path
from fit_acquisition.lang import load_translations

from fit_acquisition.tasks.nettools.headers import TaskHeaders


from fit_acquisition.tests.tasks.tasks_ui import Ui_MainWindow

app = QApplication(sys.argv)

from fit_configurations.logger import LogConfigTools
import logging.config

logger = logging.getLogger("view.scrapers.web.web")


class TaskHeadersTest(unittest.TestCase):
    folder = ""
    window = None
    translations = load_translations()

    @classmethod
    def setUpClass(cls):
        log_tools = LogConfigTools()
        log_tools.set_dynamic_loggers()
        log_tools.change_filehandlers_path(cls.folder)
        logging.config.dictConfig(log_tools.config)

        cls.task = TaskHeaders(
            logger,
            cls.window.progressBar,
            cls.window.statusbar,
        )

        cls.task.options = {"url": "http://google.it"}

    def test_00_init_packet_capture_task(self):
        self.assertEqual(self.task.label, self.translations["HEADERS"])
        self.assertEqual(self.task.state, State.INITIALIZATED)
        self.assertEqual(self.task.status, Status.SUCCESS)
        self.assertEqual(self.task.progress_bar.value(), 0)

    def test_01_headers_task(self):
        spy = QSignalSpy(self.task.started)

        self.task.start()

        if spy.count() == 0:
            received = spy.wait(500)
            while received is False:
                received = spy.wait(500)

        self.assertEqual(spy.count(), 1)

        self.assertEqual(self.task.state, State.STARTED)
        self.assertEqual(self.task.status, Status.SUCCESS)

        self.assertEqual(
            self.task.status_bar.currentMessage(),
            self.translations["HEADERS_STARTED"],
        )
        self.assertEqual(self.task.progress_bar.value(), 0)

        spy = QSignalSpy(self.task.finished)

        if spy.count() == 0:
            received = spy.wait(500)
            while received is False:
                received = spy.wait(500)

        self.assertEqual(spy.count(), 1)
        self.assertEqual(self.task.state, State.COMPLETED)
        self.assertEqual(self.task.status, Status.SUCCESS)

        self.assertEqual(
            self.task.status_bar.currentMessage(),
            self.translations["HEADERS_COMPLETED"],
        )

        self.assertTrue(os.path.exists(os.path.join(self.folder, "headers.txt")))


if __name__ == "__main__":

    folder = resolve_path("acquisition/tasks/headers_test_folder")

    if not os.path.exists(folder):
        os.makedirs(folder)

    MainWindow = QtWidgets.QMainWindow()
    TaskHeadersTest.folder = folder
    TaskHeadersTest.window = Ui_MainWindow()
    TaskHeadersTest.window.setupUi(MainWindow)
    TaskHeadersTest.window.progressBar.setValue(0)

    unittest.main()
