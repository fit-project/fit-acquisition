import os
import sys
import unittest

import logging

from PyQt6 import QtWidgets
from PyQt6.QtWidgets import QApplication
from PyQt6.QtTest import QSignalSpy
from common.constants.view.tasks import labels, state, status


from view.acquisition.acquisition import Acquisition
from view.tasks.info import TasksInfo
from view.tasks.nettools.whois import TaskWhois

from common.utility import resolve_path
from common.constants import logger as Logger

from tests.tasks.tasks_ui import Ui_MainWindow

app = QApplication(sys.argv)

logger = logging.getLogger("view.web.web")


class TaskWhoisTest(unittest.TestCase):
    folder = ""
    acquisition = None
    tasks_info = None
    window = None
    increment = 0

    @classmethod
    def setUpClass(cls):
        options = {"url": "https://google.it"}

        cls.task = TaskWhois(
            options,
            cls.acquisition.logger,
            cls.tasks_info,
            cls.window.progressBar,
            cls.window.statusbar,
        )

        cls.intial_progress_bar_value = cls.window.progressBar.value()
        cls.task.increment = cls.increment

    def test_00_init_headers_task(self):
        self.assertEqual(self.task.label, labels.WHOIS)
        self.assertEqual(self.task.state, state.INITIALIZATED)
        self.assertEqual(self.task.status, status.DONE)
        self.assertEqual(self.task.progress_bar.value(), 0)

        row = self.tasks_info.get_row(labels.WHOIS)
        if row >= 0:
            self.assertEqual(
                self.task.state,
                self.tasks_info.table.item(row, 1).text(),
            )
            self.assertEqual(
                self.task.status,
                self.tasks_info.table.item(row, 2).text(),
            )

    def test_01_headers_task(self):
        spy = QSignalSpy(self.task.started)

        self.task.start()

        if len(spy) == 0:
            received = spy.wait(500)
            while received is False:
                received = spy.wait(500)

        self.assertEqual(len(spy), 1)

        self.assertEqual(self.task.state, state.STARTED)
        self.assertEqual(self.task.status, status.SUCCESS)

        self.assertEqual(
            self.task.status_bar.currentMessage(),
            Logger.WHOIS_STARTED,
        )
        self.assertEqual(self.task.progress_bar.value(), 0)

        spy = QSignalSpy(self.task.finished)

        if len(spy) == 0:
            received = spy.wait(500)
            while received is False:
                received = spy.wait(500)

        self.assertEqual(len(spy), 1)
        self.assertEqual(self.task.state, state.COMPLETED)
        self.assertEqual(self.task.status, status.SUCCESS)

        self.assertEqual(
            self.task.status_bar.currentMessage(),
            Logger.WHOIS_COMPLETED,
        )
        self.assertEqual(
            self.task.progress_bar.value(),
            (self.intial_progress_bar_value + self.increment),
        )

        self.assertTrue(os.path.exists(os.path.join(self.folder, "whois.txt")))


if __name__ == "__main__":
    folder = resolve_path("tests/tasks/whois_test_folder")

    if not os.path.exists(folder):
        os.makedirs(folder)

    MainWindow = QtWidgets.QMainWindow()

    TaskWhoisTest.folder = folder
    TaskWhoisTest.acquisition = Acquisition(logger, folder)
    TaskWhoisTest.tasks_info = TasksInfo()
    TaskWhoisTest.window = Ui_MainWindow()
    TaskWhoisTest.window.setupUi(MainWindow)
    TaskWhoisTest.increment = TaskWhoisTest.acquisition.calculate_increment(1)

    TaskWhoisTest.acquisition.start()

    unittest.main()
