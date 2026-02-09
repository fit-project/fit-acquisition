#!/usr/bin/env python3
# -*- coding:utf-8 -*-
######
# -----
# Copyright (c) 2023 FIT-Project
# SPDX-License-Identifier: GPL-3.0-only
# -----
######

import os
from urllib.parse import urlparse

import scapy.all as scapy
from fit_common.core import debug, get_context, log_exception
from fit_common.gui.utils import Status

from fit_acquisition.tasks.task import Task
from fit_acquisition.tasks.task_worker import TaskWorker


class TracerouteWorker(TaskWorker):

    def __traceroute(self, url, filename):
        try:
            parsed_url = urlparse(url)
            netloc = parsed_url.netloc

            if not netloc:
                raise ValueError(self.translations["MALFORMED_URL_ERROR"])

            netloc = netloc.split(":")[0]

            with open(filename, "w") as f:
                ans, unans = scapy.sr(
                    scapy.IP(dst=netloc, ttl=(1, 22), id=scapy.RandShort())
                    / scapy.TCP(flags=0x2),
                    timeout=10,
                    verbose=False,
                )

                for snd, rcv in ans:
                    line = (
                        f"TTL={snd.ttl} IP={rcv.src} "
                        f"TCP_response={isinstance(rcv.payload, scapy.TCP)}"
                    )
                    f.write(line + "\n")

            self.finished.emit()

        except Exception as e:
            log_exception(e, context=get_context(self))
            debug(
                "Start traceroute failed",
                str(e),
                context=get_context(self),
            )
            self.error.emit(
                {
                    "title": self.translations["TRACEROUTE_ERROR_TITLE"],
                    "message": self.translations["TRACEROUTE_EXECUTION_ERROR"],
                    "details": str(e),
                }
            )

    def start(self):
        self.started.emit()
        self.__traceroute(
            self.options["url"],
            os.path.join(self.options["acquisition_directory"], "traceroute.txt"),
        )


class TaskTraceroute(Task):
    def __init__(self, logger, progress_bar=None, status_bar=None):
        super().__init__(
            logger,
            progress_bar,
            status_bar,
            label="TRACEROUTE",
            worker_class=TracerouteWorker,
        )

    def start(self):
        super().start_task(self.translations["TRACEROUTE_STARTED"])

    def _finished(self, status=Status.SUCCESS, details=""):
        super()._finished(
            status,
            details,
            self.translations["TRACEROUTE_GET_INFO_URL"].format(
                status.name, self.options["url"]
            ),
        )
