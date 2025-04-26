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

from PySide6 import QtWidgets
from PySide6.QtWidgets import QApplication
from PySide6.QtTest import QSignalSpy

from fit_common.gui.utils import State, Status
from fit_common.core.utils import resolve_path
from fit_acquisition.lang import load_translations

from fit_acquisition.tasks.infinite_loop.packetcapture import TaskPacketCapture


from fit_acquisition.tests.tasks.tasks_ui import Ui_MainWindow

from fit_configurations.logger import LogConfigTools
import logging.config

app = QApplication(sys.argv)

logger = logging.getLogger("view.scrapers.web.web")


class TaskPacketCaptureTest(unittest.TestCase):
    folder = ""
    window = None
    translations = load_translations()

    @classmethod
    def setUpClass(cls):
        log_tools = LogConfigTools()
        log_tools.change_filehandlers_path(cls.folder)
        logging.config.dictConfig(log_tools.config)

        cls.task = TaskPacketCapture(
            logger,
            cls.window.progressBar,
            cls.window.statusbar,
        )

        cls.task.options = {"acquisition_directory": cls.folder}

    def test_00_init_packet_capture_task(self):
        self.assertEqual(self.task.label, self.translations["PACKET_CAPTURE"])
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
            self.translations["NETWORK_PACKET_CAPTURE_STARTED"],
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
            self.translations["NETWORK_PACKET_CAPTURE_STARTED_DETAILS"],
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
            self.translations["NETWORK_PACKET_CAPTURE_COMPLETED"],
        )

        self.assertEqual(
            self.task.status_bar.currentMessage(),
            self.task.details,
            self.translations["NETWORK_PACKET_CAPTURE_COMPLETED_DETAILS"],
        )

        self.assertEqual(self.task.progress_bar.value(), 0)

        self.assertTrue(
            os.path.exists(os.path.join(self.folder, self.task.options["filename"]))
        )


if __name__ == "__main__":
    folder = resolve_path("acquisition/tasks/packetcapture_test_folder")

    if not os.path.exists(folder):
        os.makedirs(folder)

    MainWindow = QtWidgets.QMainWindow()

    TaskPacketCaptureTest.folder = folder
    TaskPacketCaptureTest.window = Ui_MainWindow()
    TaskPacketCaptureTest.window.setupUi(MainWindow)
    TaskPacketCaptureTest.window.progressBar.setValue(0)

    unittest.main()
