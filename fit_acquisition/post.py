#!/usr/bin/env python3
# -*- coding:utf-8 -*-
######
# -----
# Copyright (c) 2023 FIT-Project
# SPDX-License-Identifier: GPL-3.0-only
# -----
######

import os
from PySide6.QtCore import QObject, Signal

from fit_acquisition.tasks_handler import TasksHandler
from fit_acquisition.class_names import *


class PostAcquisition(QObject):
    finished = Signal()

    def __init__(self):
        self.task_handler = TasksHandler()
        super().__init__()

    def start_post_acquisition_sequence(self, increment, options):
        self.options = options
        self.increment = increment
        self.__save_case_info()

    def __save_case_info(self):
        task = self.task_handler.get_task(SAVE_CASE_INFO)
        if task:
            task.finished.connect(self.__zip_and_remove)
            task.options = self.options
            task.increment = self.increment
            task.start()

    def __zip_and_remove(self):
        if (
            self.options.get("type") == "web"
            or self.options.get("type") == "entire_website"
        ):
            self.options["acquisition_content_directory"] = os.path.join(
                self.options.get("acquisition_directory"), "acquisition_page"
            )
        elif self.options.get("type") == "email":
            self.options["acquisition_content_directory"] = os.path.join(
                self.options.get("acquisition_directory"), "acquisition_mail"
            )
        elif self.options.get("type") == "instagram":
            self.options["acquisition_content_directory"] = self.options.get(
                "profile_dir"
            )
        elif self.options.get("type") == "video":
            self.options["acquisition_content_directory"] = self.options.get("url_dir")

        task = self.task_handler.get_task(ZIP_AND_REMOVE_FOLDER)
        if task:
            task.finished.connect(self.__calculate_acquisition_file_hash)
            task.options = self.options
            task.increment = self.increment
            task.start()

    def __calculate_acquisition_file_hash(self):
        task = self.task_handler.get_task(HASH)
        if task:
            task.finished.connect(self.__generate_pdf_report)
            task.options = self.options
            task.increment = self.increment
            task.start()

    def __generate_pdf_report(self):
        task = self.task_handler.get_task(REPORT)
        if (
            self.options.get("type") == "web"
            or self.options.get("type") == "entire_website"
        ):
            self.options["pdf_filename"] = "acquisition_report.pdf"
        elif self.options.get("type") == "email":
            self.options["pdf_filename"] = "acquisition_report.pdf"
        elif self.options.get("type") == "instagram":
            self.options["pdf_filename"] = "acquisition_report.pdf"
        elif self.options.get("type") == "video":
            self.options["pdf_filename"] = "acquisition_report.pdf"
        if task:
            task.finished.connect(self.__generate_timestamp_report)
            task.options = self.options
            task.increment = self.increment
            task.start()

    def __generate_timestamp_report(self):
        task = self.task_handler.get_task(TIMESTAMP)
        if task:
            task.finished.connect(self.__send_pec_and_download_eml)
            task.options = self.options
            task.increment = self.increment
            task.start()
        else:
            task.finished.connect(self.finished.emit)

    def __send_pec_and_download_eml(self):
        task = self.task_handler.get_task(PEC_AND_DOWNLOAD_EML)
        if task:
            task.finished.connect(self.finished.emit)
            task.options = self.options
            task.increment = self.increment
            task.start()
        else:
            self.finished.emit()
