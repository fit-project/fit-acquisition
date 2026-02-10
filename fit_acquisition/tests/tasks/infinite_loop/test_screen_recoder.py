#!/usr/bin/env python3
# -*- coding:utf-8 -*-
######
# -----
# Copyright (c) 2023 FIT-Project
# SPDX-License-Identifier: GPL-3.0-only
# -----
######

import glob
import logging
import logging.config
import os

import pytest
from fit_common.core import resolve_path
from fit_common.gui.utils import State, Status
from PySide6.QtWidgets import QMainWindow

from fit_acquisition.lang import load_translations
from fit_acquisition.logger import LogConfigTools
from fit_acquisition.logger_names import LoggerName
from fit_acquisition.tasks.infinite_loop.screen_recorder import TaskScreenRecorder
from fit_acquisition.tests.tasks.tasks_ui import Ui_MainWindow

translations = load_translations()
logger = logging.getLogger(LoggerName.SCRAPER_WEB.value)


@pytest.fixture(scope="module")
def test_folder():
    folder = resolve_path("acquisition/tasks/screenrecorder_test_folder")
    os.makedirs(folder, exist_ok=True)
    return folder


@pytest.fixture
def main_window(qtbot):
    window = QMainWindow()
    qtbot.addWidget(window)
    ui = Ui_MainWindow()
    ui.setupUi(window)
    ui.progressBar.setValue(0)
    window.show()
    return window, ui


@pytest.fixture
def task_instance(main_window, test_folder):
    window, ui = main_window

    log_tools = LogConfigTools()
    log_tools.change_filehandlers_path(test_folder)
    logging.config.dictConfig(log_tools.config)

    task = TaskScreenRecorder(
        logger,
        ui.progressBar,
        ui.statusbar,
    )

    task.options = {
        "acquisition_directory": test_folder,
        "window_pos": window.pos(),
    }

    return task, ui


def test_init_screen_recorder_task(task_instance):
    task, _ = task_instance

    assert task.label == translations["SCREEN_RECORDER"]
    assert task.state == State.INITIALIZATED
    assert task.status == Status.SUCCESS
    assert task.progress_bar.value() == 0


def test_screen_recorder_task(task_instance, test_folder, qtbot):
    task, ui = task_instance

    with qtbot.waitSignal(task.started, timeout=3000):
        task.start()

    assert task.state == State.STARTED
    assert task.status in [Status.PENDING, Status.SUCCESS]
    assert task.progress_bar.value() == 0
    assert ui.statusbar.currentMessage() == translations["SCREEN_RECORDER_STARTED"]

    qtbot.wait(5000)

    with qtbot.waitSignal(task.finished, timeout=6000):
        task.increment = 100
        task.stop()

    assert task.state == State.COMPLETED
    assert task.status == Status.SUCCESS
    assert task.details == translations["NETWORK_PACKET_CAPTURE_COMPLETED_DETAILS"]
    assert ui.statusbar.currentMessage() == translations[
        "SCREEN_RECORDER_COMPLETED"
    ].format(task.status.name)
    assert task.progress_bar.value() == 100

    # Verifica che sia stato creato almeno un file (video o audio + video)
    matching_files = glob.glob(task.options["filename"] + ".*")
    assert len(matching_files) > 0
