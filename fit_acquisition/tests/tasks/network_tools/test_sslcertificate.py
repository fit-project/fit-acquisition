#!/usr/bin/env python3
# -*- coding:utf-8 -*-
######
# -----
# Copyright (c) 2023 FIT-Project
# SPDX-License-Identifier: GPL-3.0-only
# -----
######

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
from fit_acquisition.tasks.network_tools.sslcertificate import TaskSSLCertificate
from fit_acquisition.tests.tasks.tasks_ui import Ui_MainWindow

translations = load_translations()
logger = logging.getLogger(LoggerName.SCRAPER_WEB.value)


@pytest.fixture(scope="module")
def test_folder():
    folder = resolve_path("acquisition/tasks/sslcertificate_test_folder")
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
    log_tools.set_dynamic_loggers()
    log_tools.change_filehandlers_path(test_folder)
    logging.config.dictConfig(log_tools.config)

    task = TaskSSLCertificate(
        logger,
        ui.progressBar,
        ui.statusbar,
    )

    task.options = {"url": "http://google.it"}
    return task, ui


def test_init_sslcertificate_task(task_instance):
    task, _ = task_instance

    assert task.label == translations["SSLCERTIFICATE"]
    assert task.state == State.INITIALIZATED
    assert task.status == Status.SUCCESS
    assert task.progress_bar.value() == 0


def test_sslcertificate_task(task_instance, qtbot):
    task, ui = task_instance

    with qtbot.waitSignal(task.started, timeout=3000):
        task.start()

    assert task.state == State.STARTED
    assert task.status == Status.SUCCESS
    assert task.details == ""
    assert task.status_bar.currentMessage() == translations["SSLCERTIFICATE_STARTED"]
    assert task.progress_bar.value() == 0

    with qtbot.waitSignal(task.finished, timeout=3000):
        task.increment = 100
        pass

    assert task.state == State.COMPLETED
    assert task.status == Status.SUCCESS
    assert ui.statusbar.currentMessage() == translations[
        "SSLCERTIFICATE_GET_FROM_URL"
    ].format(task.status.name, task.options["url"])
    assert task.progress_bar.value() == 100

    assert os.path.exists(os.path.join(test_folder, "server.cer"))
