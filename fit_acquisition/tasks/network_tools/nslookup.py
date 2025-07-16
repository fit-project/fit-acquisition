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

from fit_common.gui.utils import Status
from fit_configurations.controller.tabs.network.network_check import (
    NetworkCheckController,
)
from nslookup import Nslookup

from fit_acquisition.tasks.task import Task
from fit_acquisition.tasks.task_worker import TaskWorker


class NslookupWorker(TaskWorker):
    logger = logging.getLogger("nslookup")

    def __nslookup(self, url, dns_server, enable_verbose_mode, enable_tcp):
        parsed_url = urlparse(url)
        netloc = parsed_url.netloc

        if not netloc:
            raise ValueError(self.translations["MALFORMED_URL_ERROR"])

        netloc = netloc.split(":")[0]

        dns_query = Nslookup(
            dns_servers=[dns_server], verbose=enable_verbose_mode, tcp=enable_tcp
        )

        ips_record = dns_query.dns_lookup(netloc)

        if ips_record.response_full:
            return "\n".join(map(str, ips_record.response_full))
        else:
            raise RuntimeError(self.translations["NSLOOKUP_NO_RESPONSE"].format(netloc))

    def start(self):
        self.started.emit()
        try:
            result = self.__nslookup(
                self.options["url"],
                self.options["nslookup_dns_server"],
                self.options["nslookup_enable_verbose_mode"],
                self.options["nslookup_enable_tcp"],
            )
            self.logger.info(result)
            self.finished.emit()

        except ValueError as e:
            self.error.emit(
                {
                    "title": self.translations["NSLOOKUP_ERROR_TITLE"],
                    "message": str(e),
                    "details": str(e),
                }
            )
        except Exception as e:
            self.error.emit(
                {
                    "title": self.translations["NSLOOKUP_ERROR_TITLE"],
                    "message": self.translations["NSLOOKUP_EXECUTION_ERROR"],
                    "details": str(e),
                }
            )


class TaskNslookup(Task):
    def __init__(self, logger, progress_bar=None, status_bar=None):
        super().__init__(
            logger,
            progress_bar,
            status_bar,
            label="NSLOOKUP",
            worker_class=NslookupWorker,
        )

    @Task.options.getter
    def options(self):
        return self._options

    @options.setter
    def options(self, options):
        url = options["url"]
        options = NetworkCheckController().configuration
        options["url"] = url
        self._options = options
    
    def start(self):
        super().start_task(self.translations["NSLOOKUP_STARTED"])

    def _finished(self, status=Status.SUCCESS, details=""):
        if status == Status.SUCCESS:
            details = self.translations["NSLOOKUP_COMPLETED"]

        message = self.translations["NSLOOKUP_GET_INFO_URL"].format(
            status.name, self.options["url"]
        )

        super()._finished(status, details, message)