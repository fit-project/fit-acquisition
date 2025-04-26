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
import time

from PySide6 import QtWidgets, QtCore
from PySide6.QtWidgets import QApplication
from PySide6.QtTest import QSignalSpy

from fit_common.gui.utils import State, Status
from fit_common.core.utils import resolve_path
from fit_acquisition.lang import load_translations

from fit_acquisition.tasks.nettools.traceroute import TaskTraceroute


from fit_acquisition.tests.tasks.tasks_ui import Ui_MainWindow

app = QApplication(sys.argv)

from fit_configurations.logger import LogConfigTools
import logging.config

logger = logging.getLogger("view.scrapers.web.web")


class TaskTracerouteTest(unittest.TestCase):
    folder = ""
    window = None
    translations = load_translations()

    @classmethod
    def setUpClass(cls):
        log_tools = LogConfigTools()
        log_tools.change_filehandlers_path(cls.folder)
        logging.config.dictConfig(log_tools.config)

        cls.task = TaskTraceroute(
            logger,
            cls.window.progressBar,
            cls.window.statusbar,
        )

        cls.task.options = {
            "acquisition_directory": cls.folder,
            "url": "https://google.it",
        }

    def test_00_init_packet_capture_task(self):
        self.assertEqual(self.task.label, self.translations["TRACEROUTE"])
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
            self.translations["TRACEROUTE_STARTED"],
        )
        self.assertEqual(self.task.progress_bar.value(), 0)

        spy = QSignalSpy(self.task.finished)
        self.task.increment = 100

        if spy.count() == 0:
            received = spy.wait(500)
            while received is False:
                received = spy.wait(500)

        self.assertEqual(spy.count(), 1)
        self.assertEqual(self.task.state, State.COMPLETED)
        self.assertEqual(self.task.status, Status.SUCCESS)

        self.assertEqual(
            self.task.status_bar.currentMessage(),
            self.translations["TRACEROUTE_COMPLETED"],
        )

        self.assertEqual(self.task.progress_bar.value(), 100)

        self.assertTrue(os.path.exists(os.path.join(self.folder, "traceroute.txt")))


if __name__ == "__main__":

    folder = resolve_path("acquisition/tasks/traceroute_test_folder")

    if not os.path.exists(folder):
        os.makedirs(folder)

    MainWindow = QtWidgets.QMainWindow()
    TaskTracerouteTest.folder = folder
    TaskTracerouteTest.window = Ui_MainWindow()
    TaskTracerouteTest.window.setupUi(MainWindow)
    TaskTracerouteTest.window.progressBar.setValue(0)
    MainWindow.show()

    unittest.main()
