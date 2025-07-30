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
from fit_acquisition.tasks.post_acquisition.zip_and_remove_folder import (
    TaskZipAndRemoveFolder,
)
from fit_acquisition.tests.tasks.tasks_ui import Ui_MainWindow

translations = load_translations()
logger = logging.getLogger("view.scrapers.web.web")


@pytest.fixture(scope="module")
def acquisition_files():
    acquisition_directory = resolve_path(
        "acquisition/tasks/zip_and_remove_folder_test_folder"
    )
    acquisition_content_directory = os.path.join(
        acquisition_directory, "acquisition_content"
    )
    downloads = os.path.join(acquisition_directory, "downloads")

    os.makedirs(acquisition_content_directory, exist_ok=True)
    os.makedirs(downloads, exist_ok=True)

    pdf_filename = "acquisition_report.pdf"
    tsr_filename = "timestamp.tsr"
    crt_filename = "tsa.crt"

    # Creazione file PDF fittizio
    with open(os.path.join(acquisition_content_directory, pdf_filename), "w") as f:
        f.write("This is not pdf file \n")

    # Creazione file TSR fittizio
    with open(os.path.join(acquisition_content_directory, tsr_filename), "w") as f:
        f.write("This is not tsr file \n")

    # Creazione file CRT fittizio
    with open(os.path.join(downloads, crt_filename), "w") as f:
        f.write("This is not crt file \n")

    return {
        "acquisition_directory": acquisition_directory,
        "acquisition_content_directory": acquisition_content_directory,
        "downloads": downloads,
        "pdf_filename": pdf_filename,
        "tsr_filename": tsr_filename,
        "crt_filename": crt_filename,
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

    task = TaskZipAndRemoveFolder(
        logger,
        ui.progressBar,
        ui.statusbar,
    )

    task.options = {
        "acquisition_directory": acquisition_files["acquisition_directory"],
        "acquisition_content_directory": acquisition_files[
            "acquisition_content_directory"
        ],
    }

    return task, ui


def test_init_zip_and_remove_folder_task(task_instance):
    task, _ = task_instance

    assert task.label == translations["ZIP_AND_REMOVE_FOLDER"]
    assert task.state == State.INITIALIZATED
    assert task.status == Status.SUCCESS
    assert task.progress_bar.value() == 0


def test_zip_and_remove_folder_task(task_instance, qtbot, acquisition_files):
    task, ui = task_instance

    with qtbot.waitSignal(task.finished, timeout=10000):
        task.start()
        task.increment = 100

    assert task.state == State.COMPLETED
    assert task.status == Status.SUCCESS
    assert ui.statusbar.currentMessage() == translations[
        "ZIP_AND_REMOVE_FOLDER_COMPLETED"
    ].format(Status.SUCCESS.name)
    assert task.progress_bar.value() == 100

    assert os.path.exists(
        os.path.join(
            acquisition_files["acquisition_directory"], "acquisition_content.zip"
        )
    )
    assert os.path.exists(
        os.path.join(acquisition_files["acquisition_directory"], "downloads.zip")
    )
