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
from fit_configurations.logger import LogConfigTools
from PySide6.QtWidgets import QMainWindow

from fit_acquisition.lang import load_translations
from fit_acquisition.tasks.post_acquisition.pec.pec_and_download_eml import (
    TaskPecAndDownloadEml,
)
from fit_acquisition.tests.tasks.tasks_ui import Ui_MainWindow

translations = load_translations()
logger = logging.getLogger("scraper.web")


@pytest.fixture(scope="module")
def acquisition_files():
    acquisition_directory = resolve_path(
        "acquisition/tasks/pec_and_download_eml_test_folder"
    )

    os.makedirs(acquisition_directory, exist_ok=True)

    pdf_filename = "acquisition_report.pdf"
    tsr_filename = "timestamp.tsr"
    crt_filename = "tsa.crt"

    # Creazione file PDF fittizio
    with open(os.path.join(acquisition_directory, pdf_filename), "w") as f:
        f.write("This is not pdf file \n")

    # Creazione file TSR fittizio
    with open(os.path.join(acquisition_directory, tsr_filename), "w") as f:
        f.write("This is not tsr file \n")

    # Creazione file CRT fittizio
    with open(os.path.join(acquisition_directory, crt_filename), "w") as f:
        f.write("This is not crt file \n")

    return {
        "acquisition_directory": acquisition_directory,
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

    task = TaskPecAndDownloadEml(
        logger,
        ui.progressBar,
        ui.statusbar,
    )

    case_info = {
        "id": 1,
        "name": "Go out",
        "lawyer_name": "",
        "operator": "",
        "proceeding_type": 1,
        "courthouse": "",
        "proceeding_number": "",
        "notes": "",
        "logo_bin": "",
        "logo": "",
        "logo_height": "",
        "logo_width": "",
    }

    task.options = {
        "acquisition_directory": acquisition_files["acquisition_directory"],
        "type": "web",
        "case_info": case_info,
    }

    return task, ui


def test_init_pec_and_download_eml_task(task_instance):
    task, _ = task_instance

    assert task.label == translations["PEC_AND_DOWNLOAD_EML"]
    assert task.state == State.INITIALIZATED
    assert task.status == Status.SUCCESS
    assert task.progress_bar.value() == 0


def test_pec_and_download_eml_task(task_instance, qtbot, acquisition_files):
    task, ui = task_instance

    # Avvia e aspetta il segnale started
    with qtbot.waitSignal(task.started, timeout=2000):
        task.start()

    assert task.state == State.STARTED
    assert task.status == Status.SUCCESS
    assert task.details == ""
    assert (
        task.status_bar.currentMessage() == translations["PEC_AND_DOWNLOAD_EML_STARTED"]
    )
    assert task.progress_bar.value() == 0

    with qtbot.waitSignal(task.finished, timeout=40000):
        task.increment = 100

    # Check final state
    assert task.state == State.COMPLETED, f"Task not completed: {task.details}"
    assert task.status == Status.SUCCESS, f"Task failed: {task.details}"
    assert ui.statusbar.currentMessage() == translations["EML_DOWNLOAD"].format(
        Status.SUCCESS.name
    )
    assert task.progress_bar.value() == 100

    # Check che almeno un file .eml esista
    eml_files = glob.glob(
        os.path.join(acquisition_files["acquisition_directory"], "*.eml")
    )
    assert len(eml_files) > 0, "No .eml files were found in the acquisition directory."
