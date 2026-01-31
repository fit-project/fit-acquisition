#!/usr/bin/env python3
# -*- coding:utf-8 -*-
######
# -----
# Copyright (c) 2023 FIT-Project
# SPDX-License-Identifier: GPL-3.0-only
# -----
######

import logging
from urllib.parse import urlparse

import requests
from fit_common.core import debug, get_context, log_exception
from fit_common.gui.utils import Status

from fit_acquisition.tasks.task import Task
from fit_acquisition.tasks.task_worker import TaskWorker


class HeadersWorker(TaskWorker):
    logger = logging.getLogger("headers")

    def __get_headers_information(self, url):
        parsed = urlparse(url)
        if not parsed.netloc:
            raise ValueError(self.translations["MALFORMED_URL_ERROR"])
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        }
        try:
            response = requests.get(url, headers=headers, verify=False, timeout=10)
            response.raise_for_status()
            return response.headers
        except requests.exceptions.HTTPError as e:
            if e.response is not None:
                status_code = e.response.status_code
                if status_code in (400, 401, 403, 405, 406, 429):
                    # Fallback to HEAD with same headers for common anti-bot responses
                    response = requests.head(
                        url, headers=headers, verify=False, timeout=10
                    )
                    if response.status_code in (400, 401, 403, 405, 406, 429):
                        return response.headers
                    response.raise_for_status()
                    return response.headers
                # Return headers even for other HTTP errors to avoid hard-failing
                return e.response.headers
            raise ConnectionError(str(e))
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
            log_exception(e, context=get_context(self))
            debug(
                "Start headers failed",
                str(e),
                context=get_context(self),
            )
            self.error.emit(
                {
                    "title": self.translations["HEADERS_ERROR_TITLE"],
                    "message": str(e),
                    "details": str(e),
                }
            )

        except ConnectionError as e:
            log_exception(e, context=get_context(self))
            debug(
                "Start headers failed",
                str(e),
                context=get_context(self),
            )
            self.error.emit(
                {
                    "title": self.translations["HEADERS_ERROR_TITLE"],
                    "message": self.translations["HTTP_CONNECTION_ERROR"],
                    "details": str(e),
                }
            )

        except Exception as e:
            log_exception(e, context=get_context(self))
            debug(
                "Start headers failed",
                str(e),
                context=get_context(self),
            )
            self.error.emit(
                {
                    "title": self.translations["HEADERS_ERROR_TITLE"],
                    "message": self.translations["HEADERS_EXECUTION_ERROR"],
                    "details": str(e),
                }
            )


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

    def _finished(self, status=Status.SUCCESS, details=""):
        if status == Status.SUCCESS:
            details = self.translations["HEADERS_COMPLETED"]

        message = self.translations["HEADERS_GET_INFO_URL"].format(
            status.name, self.options["url"]
        )

        super()._finished(status, details, message)
