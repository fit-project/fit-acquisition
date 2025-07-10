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

from fit_acquisition.task import Task
from fit_common.gui.utils import State, Status
from fit_acquisition.lang import load_translations


class HeadersWorker(QObject):
    logger = logging.getLogger("headers")
    finished = Signal()
    started = Signal()
    error = Signal(object)

    def __init__(self):
        QObject.__init__(self)
        self.translations = load_translations()

    @property
    def url(self):
        return self._url

    @url.setter
    def url(self, url):
        self._url = url

    def __get_headers_information(self, url):
        parsed = urlparse(url)
        if not parsed.netloc:
            raise ValueError(self.translations["MALFORMED_URL_ERROR"])

        try:
            response = requests.get(url, verify=False, timeout=10)
            response.raise_for_status()
            return response.headers
        except requests.exceptions.RequestException as e:
            raise ConnectionError(str(e))

    def start(self):
        self.started.emit()
        try:
            headers = self.__get_headers_information(self.url)
            headers = dict(headers)
            for key, value in headers.items():
                self.logger.info(f"{key}: {value}")
            self.finished.emit()

        except ValueError as e:
            self.error.emit(
                {
                    "title": self.translations["HEADERS_ERROR_TITLE"],
                    "message": str(e),
                    "details": str(e),
                }
            )

        except ConnectionError as e:
            self.error.emit(
                {
                    "title": self.translations["HEADERS_ERROR_TITLE"],
                    "message": self.translations["HTTP_CONNECTION_ERROR"],
                    "details": str(e),
                }
            )

        except Exception as e:
            self.error.emit(
                {
                    "title": self.translations["HEADERS_ERROR_TITLE"],
                    "message": self.translations["HEADERS_EXECUTION_ERROR"],
                    "details": str(e),
                }
            )


class TaskHeaders(Task):
    def __init__(self, logger, progress_bar=None, status_bar=None):
        super().__init__(logger, progress_bar, status_bar)

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
        self.__finished(Status.FAILURE, error.get("details"))

    def start(self):
        self.update_task(State.STARTED, Status.PENDING)
        self.set_message_on_the_statusbar(self.translations["HEADERS_STARTED"])
        self.worker.url = self.options["url"]
        self.worker_thread.start()

    def __started(self):
        self.update_task(State.STARTED, Status.SUCCESS)
        self.started.emit()

    def __finished(self, status=Status.SUCCESS, details=""):
        self.logger.info(
            self.translations["HEADERS_GET_INFO_URL"].format(
                status.name, self.options["url"]
            )
        )
        self.set_message_on_the_statusbar(self.translations["HEADERS_COMPLETED"])
        self.update_progress_bar()

        self.update_task(State.COMPLETED, status, details)

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
