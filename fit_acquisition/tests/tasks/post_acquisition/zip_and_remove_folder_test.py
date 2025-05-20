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
import glob

from PySide6 import QtWidgets
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QEventLoop
from PySide6.QtTest import QSignalSpy

from fit_common.gui.utils import State, Status
from fit_common.core.utils import resolve_path
from fit_acquisition.lang import load_translations

from fit_acquisition.tasks.post_acquisition.zip_and_remove_folder import (
    TaskZipAndRemoveFolder,
)

from fit_acquisition.tests.tasks.tasks_ui import Ui_MainWindow

app = QApplication(sys.argv)

from fit_configurations.logger import LogConfigTools

import logging.config

logger = logging.getLogger("view.scrapers.web.web")


class TaskZipAndRemoveFolderTest(unittest.TestCase):
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

        cls.task = TaskZipAndRemoveFolder(
            logger,
            cls.window.progressBar,
            cls.window.statusbar,
        )

        acquisition_content = resolve_path(
            os.path.join(cls.folder, "acquisition_content")
        )
        os.makedirs(acquisition_content, exist_ok=True)

        downloads = resolve_path(os.path.join(cls.folder, "downloads"))
        os.makedirs(downloads, exist_ok=True)

        cls.pdf_filename = "acquisition_report.pdf"

        file = open(os.path.join(acquisition_content, cls.pdf_filename), "w")
        file.write("This is not pdf file \n")
        file.close()

        cls.tsr_filename = "timestamp.tsr"

        file = open(os.path.join(acquisition_content, cls.tsr_filename), "w")
        file.write("This is not tsr file \n")
        file.close()

        cls.crt_filename = "tsa.crt"

        file = open(os.path.join(downloads, cls.crt_filename), "w")
        file.write("This is not crt file \n")
        file.close()

        cls.task.options = {
            "acquisition_directory": cls.folder,
            "acquisition_content_directory": acquisition_content,
        }

    def test_00_init_zip_and_remove_folder_task(self):
        self.assertEqual(self.task.label, self.translations["ZIP_AND_REMOVE_FOLDER"])
        self.assertEqual(self.task.state, State.INITIALIZATED)
        self.assertEqual(self.task.status, Status.SUCCESS)
        self.assertEqual(self.task.progress_bar.value(), 0)

    def test_01_zip_and_remove_folder_task(self):
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
            self.assertTrue(
                os.path.exists(os.path.join(self.folder, "acquisition_content.zip"))
            )
            self.assertTrue(os.path.exists(os.path.join(self.folder, "downloads.zip")))
            loop.quit()

        self.task.finished.connect(on_finished)
        self.task.start()
        loop.exec()


if __name__ == "__main__":
    folder = resolve_path("acquisition/tasks/zip_and_remove_folder_test_folder")
    os.makedirs(folder, exist_ok=True)

    MainWindow = QtWidgets.QMainWindow()
    TaskZipAndRemoveFolderTest.folder = folder
    TaskZipAndRemoveFolderTest.window = Ui_MainWindow()
    TaskZipAndRemoveFolderTest.window.setupUi(MainWindow)
    TaskZipAndRemoveFolderTest.window.progressBar.setValue(0)
    MainWindow.show()

    unittest.main()
