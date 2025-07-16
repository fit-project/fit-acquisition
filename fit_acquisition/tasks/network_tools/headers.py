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

from fit_acquisition.tasks.task import Task
from fit_acquisition.tasks.task_worker import TaskWorker

from fit_common.gui.utils import Status


class HeadersWorker(TaskWorker):
    logger = logging.getLogger("headers")

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
            headers = self.__get_headers_information(self.options["url"])
            headers = dict(headers)
            for key, value in headers.items():
                self.logger.info(f"{key}: {value}")
            self.finished.emit()

        except ValueError as e:
            self.error.emit({
                "title": self.translations["HEADERS_ERROR_TITLE"],
                "message": str(e),
                "details": str(e),
            })

        except ConnectionError as e:
            self.error.emit({
                "title": self.translations["HEADERS_ERROR_TITLE"],
                "message": self.translations["HTTP_CONNECTION_ERROR"],
                "details": str(e),
            })

        except Exception as e:
            self.error.emit({
                "title": self.translations["HEADERS_ERROR_TITLE"],
                "message": self.translations["HEADERS_EXECUTION_ERROR"],
                "details": str(e),
            })


class TaskHeaders(Task):
    def __init__(self, logger, progress_bar=None, status_bar=None):
        super().__init__(
            logger,
            progress_bar,
            status_bar,
            label="HEADERS",
            worker_class=HeadersWorker,
        )

    def start(self):
        super().start_task(self.translations["HEADERS_STARTED"])

    def _started(self):
        super()._started()

    def _finished(self, status=Status.SUCCESS, details=""):
        if status == Status.SUCCESS:
            details = self.translations["HEADERS_COMPLETED"]

        message = self.translations["HEADERS_GET_INFO_URL"].format(
            status.name, self.options["url"]
        )

        super()._finished(status, details, message)
