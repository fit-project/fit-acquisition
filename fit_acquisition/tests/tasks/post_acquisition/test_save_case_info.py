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
from fit_acquisition.tasks.post_acquisition.save_case_info import TaskSaveCaseInfo
from fit_acquisition.tests.tasks.tasks_ui import Ui_MainWindow

translations = load_translations()
logger = logging.getLogger("view.scrapers.web.web")


@pytest.fixture(scope="module")
def test_folder():
    folder = resolve_path("acquisition/tasks/save_case_info")
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

    task = TaskSaveCaseInfo(
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
        "acquisition_directory": test_folder,
        "case_info": case_info,
    }

    return task, ui


def test_init_save_case_info_task(task_instance):
    task, _ = task_instance

    assert task.label == translations["SAVE_CASE_INFO"]
    assert task.state == State.INITIALIZATED
    assert task.status == Status.SUCCESS
    assert task.progress_bar.value() == 0


def test_save_case_info_task(task_instance, qtbot, test_folder):
    task, ui = task_instance

    with qtbot.waitSignal(task.finished, timeout=3000):
        task.start()
        task.increment = 100

    assert task.state == State.COMPLETED
    assert task.status == Status.SUCCESS
    assert ui.statusbar.currentMessage() == translations[
        "SAVE_CASE_INFO_COMPLETED"
    ].format(task.status.name)
    assert task.progress_bar.value() == 100

    assert os.path.exists(os.path.join(test_folder, "caseinfo.json"))
