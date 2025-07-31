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
from fit_configurations.logger import LogConfigTools
from PySide6.QtWidgets import QMainWindow

from fit_acquisition.lang import load_translations
from fit_acquisition.tasks.post_acquisition.timestamp import TaskTimestamp
from fit_acquisition.tests.tasks.tasks_ui import Ui_MainWindow

translations = load_translations()
logger = logging.getLogger("scraper.web")


@pytest.fixture(scope="module")
def acquisition_files():
    acquisition_directory = resolve_path("acquisition/tasks/timestamp_test_folder")
    os.makedirs(acquisition_directory, exist_ok=True)

    pdf_filename = "acquisition_report.pdf"

    # Creazione file PDF fittizio
    with open(os.path.join(acquisition_directory, pdf_filename), "w") as f:
        f.write("This is not pdf file \n")

    return {
        "acquisition_directory": acquisition_directory,
        "pdf_filename": pdf_filename,
    }


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
def task_instance(main_window, acquisition_files):
    window, ui = main_window

    log_tools = LogConfigTools()
    log_tools.set_dynamic_loggers()
    log_tools.change_filehandlers_path(acquisition_files["acquisition_directory"])
    logging.config.dictConfig(log_tools.config)

    task = TaskTimestamp(
        logger,
        ui.progressBar,
        ui.statusbar,
    )

    task.options = {
        "acquisition_directory": acquisition_files["acquisition_directory"],
        "pdf_filename": "acquisition_report.pdf",
    }

    return task, ui


def test_init_timestamp_task(task_instance):
    task, _ = task_instance

    assert task.label == translations["TIMESTAMP"]
    assert task.state == State.INITIALIZATED
    assert task.status == Status.SUCCESS
    assert task.progress_bar.value() == 0


def test_timestamp_task(task_instance, qtbot, acquisition_files):
    task, ui = task_instance

    with qtbot.waitSignal(task.finished, timeout=10000):
        task.start()
        task.increment = 100

    print("Task status:", task.status)
    print("Task details:", task.details)
    print("Status bar:", ui.statusbar.currentMessage())

    assert task.state == State.COMPLETED
    assert task.status == Status.SUCCESS
    assert ui.statusbar.currentMessage() == translations["TIMESTAMP_APPLY"].format(
        Status.SUCCESS.name, task.options["pdf_filename"], task.options["server_name"]
    )
    assert task.progress_bar.value() == 100

    assert os.path.exists(
        os.path.join(acquisition_files["acquisition_directory"], "timestamp.tsr")
    )
    assert os.path.exists(
        os.path.join(acquisition_files["acquisition_directory"], "tsa.crt")
    )
