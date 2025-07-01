#!/usr/bin/env python3
# -*- coding:utf-8 -*-

import os
import sys
import logging.config

from PySide6 import QtWidgets
from PySide6.QtCore import Qt
from fit_common.core.utils import resolve_path

from fit_acquisition.acquisition import Acquisition
from fit_acquisition.tasks_info import TasksInfo
from fit_acquisition.class_names import *

from fit_configurations.logger import LogConfigTools

import fit_acquisition.tasks.infinite_loop
import fit_acquisition.tasks.nettools
import fit_acquisition.tasks.post_acquisition
import fit_acquisition.tasks.post_acquisition.pec
import fit_acquisition.tasks.post_acquisition.report

from fit_acquisition.lang import load_translations


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self, acquisition):
        super().__init__()
        self.setWindowTitle("Manual Acquisition Test")
        self.setGeometry(100, 100, 800, 600)

        # === Central widget
        central = QtWidgets.QWidget()
        self.setCentralWidget(central)
        layout = QtWidgets.QVBoxLayout(central)

        self.progress = QtWidgets.QProgressBar()
        self.status_bar = QtWidgets.QStatusBar()
        self.setStatusBar(self.status_bar)

        self.start_btn = QtWidgets.QPushButton("Start")
        self.stop_btn = QtWidgets.QPushButton("Stop")

        layout.addWidget(self.progress)
        layout.addWidget(self.start_btn)
        layout.addWidget(self.stop_btn)

        self.acquisition = acquisition
        self.tasks_info = None

        # Lo ridimensioniamo dinamicamente
        self.resizeEvent = self.on_resize

        self.start_btn.clicked.connect(self.acquisition.start)
        self.stop_btn.clicked.connect(self.on_stop)

        self.translations = load_translations()

    def on_resize(self, event):
        self.tasks_info.setGeometry(self.rect())

    def on_stop(self):
        self.tasks_info.setGeometry(self.rect())
        self.tasks_info.show()
        self.acquisition.stop()
        self.acquisition.stop_tasks_is_finished.connect(self.on_stop_tasks_finished)

    def on_stop_tasks_finished(self):
        print("MA PERCHE'")
        # Post acquisizione
        self.acquisition.post_acquisition_is_finished.connect(self.tasks_info.close)
        self.acquisition.start_post_acquisition()


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)

    acquisition_dir = resolve_path("acquisition/manual_test_folder")
    os.makedirs(acquisition_dir, exist_ok=True)
    acquisition_page = os.path.join(acquisition_dir, "acquisition_page")
    os.makedirs(acquisition_page, exist_ok=True)

    # Logging
    log_tools = LogConfigTools()
    log_tools.set_dynamic_loggers()
    log_tools.change_filehandlers_path(acquisition_dir)
    logging.config.dictConfig(log_tools.config)

    # Setup Acquisition
    logger = logging.getLogger("view.scrapers.web.web")
    acquisition = Acquisition(
        logger=logger,
        progress_bar=None,
        status_bar=None,
        parent=None,
        packages=[
            fit_acquisition.tasks.infinite_loop,
            fit_acquisition.tasks.nettools,
            fit_acquisition.tasks.post_acquisition,
            fit_acquisition.tasks.post_acquisition.pec,
            fit_acquisition.tasks.post_acquisition.report,
        ],
    )

    # acquisition.start_tasks = [SCREENRECORDER, PACKETCAPTURE]
    acquisition.stop_tasks = [
        WHOIS,
        NSLOOKUP,
        HEADERS,
        SSLKEYLOG,
        SSLCERTIFICATE,
        TRACEROUTE,
    ]

    acquisition.post_tasks = list()

    # UI
    window = MainWindow(acquisition)
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
    acquisition.options = {
        "acquisition_directory": acquisition_dir,
        "current_widget": None,
        "window_pos": window.centralWidget().pos(),
        "url": "http://google.it",
        "type": "web",
        "case_info": case_info,
        "pdf_filename": "acquisition_report.pdf",
    }
    acquisition.load_tasks()

    window.tasks_info = TasksInfo(parent=window)
    window.tasks_info.setWindowFlags(Qt.WindowType.Widget)
    window.tasks_info.setAutoFillBackground(True)
    window.tasks_info.setGeometry(window.rect())
    window.tasks_info.hide()
    window.tasks_info.raise_()

    print("\n>>> TASKS LOADED:")
    for t in acquisition.tasks_manager.get_tasks():
        print(f"- {t.label} ({t.__class__.__name__})")

    window.acquisition.progress_bar = window.progress
    window.acquisition.status_bar = window.statusBar()
    window.show()

    sys.exit(app.exec())
