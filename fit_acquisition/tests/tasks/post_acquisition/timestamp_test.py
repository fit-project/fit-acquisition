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
from PySide6.QtCore import QEventLoop
from PySide6.QtTest import QSignalSpy

from fit_common.gui.utils import State, Status
from fit_common.core.utils import resolve_path
from fit_acquisition.lang import load_translations

from fit_acquisition.tasks.post_acquisition.timestamp import TaskTimestamp

from fit_acquisition.tests.tasks.tasks_ui import Ui_MainWindow

app = QApplication(sys.argv)

from fit_configurations.logger import LogConfigTools

import logging.config

logger = logging.getLogger("view.scrapers.web.web")


class TaskTimestampTest(unittest.TestCase):
    folder = ""
    window = None
    pdf_filename = None
    translations = load_translations()

    @classmethod
    def setUpClass(cls):
        log_tools = LogConfigTools()
        log_tools.set_dynamic_loggers()
        log_tools.change_filehandlers_path(cls.folder)
        logging.config.dictConfig(log_tools.config)

        cls.task = TaskTimestamp(
            logger,
            cls.window.progressBar,
            cls.window.statusbar,
        )

        cls.task.options = {
            "acquisition_directory": cls.folder,
            "pdf_filename": cls.pdf_filename,
        }

    def test_00_init_timestamp_task(self):
        self.assertEqual(self.task.label, self.translations["TIMESTAMP"])
        self.assertEqual(self.task.state, State.INITIALIZATED)
        self.assertEqual(self.task.status, Status.SUCCESS)
        self.assertEqual(self.task.progress_bar.value(), 0)

    def test_01_timestamp_task(self):
        spy = QSignalSpy(self.task.started)

        self.task.start()

        if spy.count() == 0:
            received = spy.wait(500)
            while received is False:
                received = spy.wait(500)

        self.assertEqual(spy.count(), 1)

        self.assertEqual(self.task.state, State.STARTED)
        self.assertEqual(self.task.status, Status.SUCCESS)

        loop = QEventLoop()
        self.task.increment = 100

        def on_finished():
            self.assertEqual(self.task.state, State.COMPLETED)
            self.assertEqual(self.task.status, Status.SUCCESS)
            self.assertEqual(self.task.progress_bar.value(), 100)
            self.assertTrue(os.path.exists(os.path.join(self.folder, "timestamp.tsr")))
            self.assertTrue(os.path.exists(os.path.join(self.folder, "tsa.crt")))
            loop.quit()

        self.task.finished.connect(on_finished)
        self.task.start()
        loop.exec()


if __name__ == "__main__":
    folder = resolve_path("acquisition/tasks/timestamp_test")
    os.makedirs(folder, exist_ok=True)

    MainWindow = QtWidgets.QMainWindow()
    TaskTimestampTest.folder = folder
    TaskTimestampTest.window = Ui_MainWindow()
    TaskTimestampTest.window.setupUi(MainWindow)
    TaskTimestampTest.window.progressBar.setValue(0)
    TaskTimestampTest.pdf_filename = "acquisition_report.pdf"
    file = open(os.path.join(folder, TaskTimestampTest.pdf_filename), "w")
    file.write("This is not pdf file \n")
    file.close()
    MainWindow.show()

    unittest.main()
