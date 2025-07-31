#!/usr/bin/env python3
# -*- coding:utf-8 -*-

import logging.config
import os
import sys

from fit_common.core import resolve_path
from fit_configurations.logger import LogConfigTools
from PySide6 import QtCore, QtWidgets
from PySide6.QtCore import Qt

from fit_acquisition.acquisition import Acquisition
from fit_acquisition.class_names import class_names
from fit_acquisition.lang import load_translations
from fit_acquisition.tasks.tasks_info import TasksInfo


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self, acquisition):
        super().__init__()
        self.setWindowTitle("Manual Acquisition Test")
        self.setGeometry(100, 100, 800, 600)

        self.acquisition = acquisition
        self.tasks_info = None

        # === Central widget
        central = QtWidgets.QWidget()
        self.setCentralWidget(central)
        layout = QtWidgets.QVBoxLayout(central)

        self.acquisition.progress_bar = QtWidgets.QProgressBar()
        self.acquisition.status_bar = QtWidgets.QLabel()

        self.start_btn = QtWidgets.QPushButton("Start")
        self.stop_btn = QtWidgets.QPushButton("Stop")

        layout.addWidget(self.acquisition.progress_bar)
        layout.addWidget(self.start_btn)
        layout.addWidget(self.stop_btn)
        layout.addWidget(self.acquisition.status_bar)

        # Lo ridimensioniamo dinamicamente
        self.resizeEvent = self.on_resize

        self.start_btn.clicked.connect(self.acquisition.run_start_tasks)
        self.stop_btn.clicked.connect(self.on_stop)

        self.translations = load_translations()

    def on_resize(self, event):
        self.tasks_info.setGeometry(self.rect())

    def on_stop(self):
        self.acquisition.stop_tasks_finished.connect(self.on_stop_tasks_finished)
        self.tasks_info.setGeometry(self.rect())
        self.tasks_info.show()
        self.acquisition.run_stop_tasks()

    def on_stop_tasks_finished(self):
        # Post acquisizione
        self.acquisition.post_acquisition_finished.connect(
            self.on_post_acquisition_finished
        )
        self.acquisition.start_post_acquisition()

    def on_post_acquisition_finished(self):
        QtCore.QTimer.singleShot(1000, self.tasks_info.close)


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
    logger = logging.getLogger("scraper.web")
    acquisition = Acquisition(logger=logger)

    acquisition.start_tasks = [class_names.SCREENRECORDER, class_names.PACKETCAPTURE]
    acquisition.stop_tasks = [
        class_names.WHOIS,
        class_names.NSLOOKUP,
        class_names.HEADERS,
        class_names.SSLKEYLOG,
        class_names.SSLCERTIFICATE,
        class_names.TRACEROUTE,
        class_names.SCREENRECORDER,
        class_names.PACKETCAPTURE,
    ]

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

    window.show()

    sys.exit(app.exec())
