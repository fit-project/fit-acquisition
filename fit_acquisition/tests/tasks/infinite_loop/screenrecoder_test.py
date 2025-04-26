#!/usr/bin/env python3
# -*- coding:utf-8 -*-
######
# -----
# Copyright (c) 2023 FIT-Project
# SPDX-License-Identifier: GPL-3.0-only
# -----
######


import os
import time
import sys
import unittest
import logging
import glob

from PySide6 import QtWidgets
from PySide6.QtWidgets import QApplication
from PySide6.QtTest import QSignalSpy

from fit_common.gui.utils import State, Status
from fit_common.core.utils import resolve_path
from fit_acquisition.lang import load_translations

from fit_acquisition.tasks.infinite_loop.screenrecorder import TaskScreenRecorder


from fit_acquisition.tests.tasks.tasks_ui import Ui_MainWindow

app = QApplication(sys.argv)

logger = logging.getLogger("view.scrapers.web.web")


class TaskScreenRecorderTest(unittest.TestCase):
    folder = ""
    window = None
    translations = load_translations()

    @classmethod
    def setUpClass(cls):
        cls.task = TaskScreenRecorder(
            logger,
            cls.window.progressBar,
            cls.window.statusbar,
        )

        cls.task.options = {
            "acquisition_directory": cls.folder,
            "window_pos": cls.window.centralwidget.pos(),
        }

    def test_00_init_packet_capture_task(self):
        self.assertEqual(self.task.label, self.translations["SCREEN_RECORDER"])
        self.assertEqual(self.task.state, State.INITIALIZATED)
        self.assertEqual(self.task.status, Status.SUCCESS)
        self.assertEqual(self.task.progress_bar.value(), 0)

    def test_01_packet_capture_task(self):
        spy = QSignalSpy(self.task.started)

        self.task.start()

        self.assertEqual(self.task.state, State.STARTED)
        self.assertEqual(self.task.status, Status.PENDING)
        self.assertEqual(
            self.task.status_bar.currentMessage(),
            self.translations["SCREEN_RECORDER_STARTED"],
        )
        self.assertEqual(self.task.progress_bar.value(), 0)
        if spy.count() == 0:
            received = spy.wait(500)
            while received is False:
                received = spy.wait(500)

        self.assertEqual(spy.count(), 1)

        self.assertEqual(self.task.state, State.STARTED)
        self.assertEqual(self.task.status, Status.SUCCESS)
        self.assertEqual(
            self.task.details,
            self.translations["SCREEN_RECORDER_STARTED_DETAILS"],
        )

        time.sleep(5)

        spy = QSignalSpy(self.task.finished)
        self.task.stop()

        if spy.count() == 0:
            received = spy.wait(500)
            while received is False:
                received = spy.wait(500)

        self.assertEqual(spy.count(), 1)
        self.assertEqual(self.task.state, State.COMPLETED)
        self.assertEqual(self.task.status, Status.SUCCESS)
        self.assertEqual(
            self.task.details,
            self.task.details,
            self.translations["SCREEN_RECORDER_COMPLETED"],
        )

        self.assertEqual(
            self.task.status_bar.currentMessage(),
            self.task.details,
            self.translations["SCREEN_RECORDER_COMPLETED_DETAILS"],
        )

        self.assertEqual(self.task.progress_bar.value(), 0)

        file_pattern = os.path.join(self.folder, self.task.options["filename"]) + ".*"
        matching_files = glob.glob(file_pattern)

        self.assertTrue(len(matching_files) > 0)


if __name__ == "__main__":
    folder = resolve_path("acquisition/tasks/screenrecorder_test_folder")

    if not os.path.exists(folder):
        os.makedirs(folder)

    MainWindow = QtWidgets.QMainWindow()

    TaskScreenRecorderTest.folder = folder
    TaskScreenRecorderTest.window = Ui_MainWindow()
    TaskScreenRecorderTest.window.setupUi(MainWindow)
    TaskScreenRecorderTest.window.progressBar.setValue(0)

    unittest.main()
