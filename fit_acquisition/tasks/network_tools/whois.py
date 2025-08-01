#!/usr/bin/env python3
# -*- coding:utf-8 -*-
######
# -----
# Copyright (c) 2023 FIT-Project
# SPDX-License-Identifier: GPL-3.0-only
# -----
######

import logging
import socket

from fit_common.core import debug, get_context, log_exception
from fit_common.gui.utils import Status
from whois import IPV4_OR_V6, NICClient, extract_domain

from fit_acquisition.tasks.task import Task
from fit_acquisition.tasks.task_worker import TaskWorker


class WhoisWorker(TaskWorker):
    logger = logging.getLogger("whois")

    def __whois(self, url, flags=0):
        ip_match = IPV4_OR_V6.match(url)
        if ip_match:
            domain = url
            result = socket.gethostbyaddr(url)  # può sollevare socket.herror
            domain = extract_domain(result[0])
        else:
            domain = extract_domain(url)

        if not domain:
            raise ValueError(self.translations["WHOIS_INVALID_DOMAIN_ERROR"])

        nic_client = NICClient()
        result = nic_client.whois_lookup(None, domain.encode("idna"), flags)

        if not result:
            raise ValueError(self.translations["WHOIS_INVALID_DOMAIN_ERROR"])

        return result

    def start(self):
        self.started.emit()
        try:
            result = self.__whois(self.options["url"])
            self.logger.info(result)
            self.finished.emit()
        except socket.herror as e:
            log_exception(e, context=get_context(self))
            debug(
                "Start whois failed",
                str(e),
                context=get_context(self),
            )
            self.error.emit(
                {
                    "title": self.translations["WHOIS_ERROR_TITLE"],
                    "message": self.translations["WHOIS_DNS_RESOLUTON_ERROR"],
                    "details": str(e),
                }
            )
        except ValueError as e:
            log_exception(e, context=get_context(self))
            debug(
                "Start whois failed",
                str(e),
                context=get_context(self),
            )
            self.error.emit(
                {
                    "title": self.translations["WHOIS_ERROR_TITLE"],
                    "message": str(e),
                    "details": str(e),
                }
            )
        except Exception as e:
            log_exception(e, context=get_context(self))
            debug(
                "Start whois failed",
                str(e),
                context=get_context(self),
            )
            self.error.emit(
                {
                    "title": self.translations["WHOIS_ERROR_TITLE"],
                    "message": self.translations["WHOIS_EXECUTION_ERROR"],
                    "details": str(e),
                }
            )


class TaskWhois(Task):
    def __init__(self, logger, progress_bar=None, status_bar=None):
        super().__init__(
            logger,
            progress_bar,
            status_bar,
            label="WHOIS",
            worker_class=WhoisWorker,
        )

    def start(self):
        super().start_task(self.translations["WHOIS_STARTED"])

    def _finished(self, status=Status.SUCCESS, details=""):
        message = self.translations["WHOIS_GET_INFO_URL"].format(
            status.name, self.options["url"]
        )
        super()._finished(status, details, message)
