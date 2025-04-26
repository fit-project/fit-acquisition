#!/usr/bin/env python3
# -*- coding:utf-8 -*-
######
# -----
# Copyright (c) 2023 FIT-Project
# SPDX-License-Identifier: GPL-3.0-only
# -----
######

import logging
import requests
from urllib.parse import urlparse
from shiboken6 import isValid

from PySide6.QtCore import QObject, Signal, QThread, QEventLoop, QTimer
from PySide6.QtWidgets import QMessageBox

from fit_acquisition.task import Task
from fit_common.gui.utils import State, Status
from fit_common.gui.error import Error as ErrorView
from fit_acquisition.lang import load_translations


class HeadersWorker(QObject):
    logger = logging.getLogger("headers")
    finished = Signal()
    started = Signal()
    error = Signal(object)

    def __init__(self, parent=None):
        QObject.__init__(self, parent=parent)
        self.translations = load_translations()

    @property
    def url(self):
        return self._url

    @url.setter
    def url(self, url):
        self._url = url

    def __get_headers_information(self, url):
        __url = urlparse(url)
        if not __url.netloc:
            self.error.emit(
                {
                    "title": self.translations["HEADERS_ERROR_TITLE"],
                    "message": self.translations["MALFORMED_URL_ERROR"],
                    "details": "",
                }
            )
        try:
            response = requests.get(url, verify=False, timeout=10)
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            self.error.emit(
                {
                    "title": self.translations["HEADERS_ERROR_TITLE"],
                    "message": self.translations["HTTP_CONNECTION_ERROR"],
                    "details": str(e),
                }
            )
        return response.headers

    def start(self):
        self.started.emit()
        headers = self.__get_headers_information(self.url)
        if headers:
            headers = dict(headers)
            for key, value in headers.items():
                self.logger.info(f"{key}: {value}")
        else:
            self.logger.error("No headers retrieved.")

        self.finished.emit()


class TaskHeaders(Task):
    def __init__(self, logger, progress_bar=None, status_bar=None, parent=None):
        super().__init__(logger, progress_bar, status_bar, parent)

        self.translations = load_translations()

        self.label = self.translations["HEADERS"]

        self.worker_thread = QThread()
        self.worker = HeadersWorker()
        self.worker.moveToThread(self.worker_thread)
        self.worker_thread.started.connect(self.worker.start)
        self.worker.started.connect(self.__started)
        self.worker.finished.connect(self.__finished)
        self.worker.error.connect(self.__handle_error)

        self.destroyed.connect(lambda: self.__destroyed_handler(self.__dict__))

    def __handle_error(self, error):
        error_dlg = ErrorView(
            QMessageBox.Icon.Critical,
            error.get("title"),
            error.get("message"),
            error.get("details"),
        )
        error_dlg.exec()

    def start(self):
        self.update_task(State.STARTED, Status.PENDING)
        self.set_message_on_the_statusbar(self.translations["HEADERS_STARTED"])
        self.worker.url = self.options["url"]
        self.worker_thread.start()

    def __started(self):
        self.update_task(State.STARTED, Status.SUCCESS)
        self.started.emit()

    def __finished(self):
        self.logger.info(
            self.translations["HEADERS_GET_INFO_URL"].format(self.options["url"])
        )
        self.set_message_on_the_statusbar(self.translations["HEADERS_COMPLETED"])
        self.update_progress_bar()

        self.update_task(State.COMPLETED, Status.SUCCESS)

        self.finished.emit()

        loop = QEventLoop()
        QTimer.singleShot(1000, loop.quit)
        loop.exec()

        self.worker_thread.quit()
        self.worker_thread.wait()

    def __destroyed_handler(self, _dict):
        if hasattr(self, "worker_thread") and isValid(self.worker_thread):
            if self.worker_thread.isRunning():
                self.worker_thread.quit()
                self.worker_thread.wait()
