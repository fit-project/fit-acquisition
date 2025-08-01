#!/usr/bin/env python3
# -*- coding:utf-8 -*-
######
# -----
# Copyright (c) 2023 FIT-Project
# SPDX-License-Identifier: GPL-3.0-only
# -----
######

import os

import requests
from fit_common.core import debug, get_context, log_exception
from fit_common.gui.utils import Status
from fit_configurations.controller.tabs.timestamp.timestamp import TimestampController
from rfc3161ng.api import RemoteTimestamper

from fit_acquisition.tasks.task import Task
from fit_acquisition.tasks.task_worker import TaskWorker


class TimestampWorker(TaskWorker):

    def start(self):
        self.started.emit()

        try:
            pdf_path = os.path.join(
                self.options["acquisition_directory"], self.options["pdf_filename"]
            )
            ts_path = os.path.join(
                self.options["acquisition_directory"], "timestamp.tsr"
            )
            cert_path = os.path.join(self.options["acquisition_directory"], "tsa.crt")

            # getting the chain from the authority
            response = requests.get(self.options["cert_url"], timeout=10)
            response.raise_for_status()  # Raise exception for HTTP status codes != 200

            with open(cert_path, "wb") as f:
                f.write(response.content)

            with open(cert_path, "rb") as f:
                certificate = f.read()

            # create the object
            rt = RemoteTimestamper(
                self.options["server_name"], certificate=certificate, hashname="sha256"
            )

            # file to be certificated
            with open(pdf_path, "rb") as f:
                timestamp = rt.timestamp(data=f.read())

            # saving the timestamp
            with open(ts_path, "wb") as f:
                f.write(timestamp)

            self.finished.emit()

        except requests.exceptions.RequestException as e:
            log_exception(e, context=get_context(self))
            debug(
                "Start timestap failed",
                str(e),
                context=get_context(self),
            )
            self.error.emit(
                {
                    "title": self.translations["TIMESTAMP_ERROR_TITLE"],
                    "message": self.translations["HTTP_CONNECTION_ERROR"],
                    "details": str(e),
                }
            )

        except (OSError, IOError) as e:
            log_exception(e, context=get_context(self))
            debug(
                "Start timestap failed",
                str(e),
                context=get_context(self),
            )
            self.error.emit(
                {
                    "title": self.translations["TIMESTAMP_ERROR_TITLE"],
                    "message": self.translations["FILE_WRITE_ERROR"],
                    "details": str(e),
                }
            )

        except Exception as e:
            log_exception(e, context=get_context(self))
            debug(
                "Start timestap failed",
                str(e),
                context=get_context(self),
            )
            self.error.emit(
                {
                    "title": self.translations["TIMESTAMP_ERROR_TITLE"],
                    "message": self.translations["TIMESTAMP_EXECUTION_ERROR"],
                    "details": str(e),
                }
            )


class TaskTimestamp(Task):
    def __init__(self, logger, progress_bar=None, status_bar=None):
        super().__init__(
            logger,
            progress_bar,
            status_bar,
            label="TIMESTAMP",
            worker_class=TimestampWorker,
        )

    @Task.options.getter
    def options(self):
        return self._options

    @options.setter
    def options(self, options):
        folder = options["acquisition_directory"]
        pdf_filename = options["pdf_filename"]
        options = TimestampController().configuration
        options["acquisition_directory"] = folder
        options["pdf_filename"] = pdf_filename
        self._options = options

    def start(self):
        super().start_task(self.translations["TIMESTAMP_STARTED"])

    def _finished(self, status=Status.SUCCESS, details=""):
        message = self.translations["TIMESTAMP_APPLY"].format(
            status.name,
            self.options["pdf_filename"],
            self.options["server_name"],
        )

        super()._finished(status, details, message)
