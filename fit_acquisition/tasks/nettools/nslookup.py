#!/usr/bin/env python3
# -*- coding:utf-8 -*-
######
# -----
# Copyright (c) 2023 FIT-Project
# SPDX-License-Identifier: GPL-3.0-only
# -----
######

import logging
from nslookup import Nslookup
from urllib.parse import urlparse
from shiboken6 import isValid

from PySide6.QtCore import QObject, Signal, QThread, QEventLoop, QTimer

from fit_acquisition.task import Task
from fit_common.gui.utils import State, Status
from fit_acquisition.lang import load_translations


from fit_configurations.controller.tabs.network.networkcheck import (
    NetworkControllerCheck as NetworkCheckController,
)


class NslookupWorker(QObject):
    logger = logging.getLogger("nslookup")
    finished = Signal()
    started = Signal()
    error = Signal(object)

    def __init__(self, parent=None):
        QObject.__init__(self, parent=parent)
        self.translations = load_translations()

    def set_options(self, options):
        self.url = options["url"]
        self.nslookup_dns_server = options["nslookup_dns_server"]
        self.nslookup_enable_tcp = options["nslookup_enable_tcp"]
        self.nslookup_enable_verbose_mode = options["nslookup_enable_verbose_mode"]

    def __nslookup(self, url, dns_server, enable_verbose_mode, enable_tcp):
        try:
            parsed_url = urlparse(url)
            netloc = parsed_url.netloc

            if not netloc:
                self.error.emit(
                    {
                        "title": self.translations["NSLOOKUP_ERROR_TITLE"],
                        "message": self.translations["MALFORMED_URL_ERROR"],
                        "details": "",
                    }
                )

            netloc = netloc.split(":")[0]

            dns_query = Nslookup(
                dns_servers=[dns_server], verbose=enable_verbose_mode, tcp=enable_tcp
            )

            ips_record = dns_query.dns_lookup(netloc)

            if ips_record.response_full:
                return "\n".join(map(str, ips_record.response_full))
            else:
                return self.translations["MALFORMED_URL_ERROR"].format(netloc)

        except Exception as e:
            self.error.emit(
                {
                    "title": self.translations["NSLOOKUP_ERROR_TITLE"],
                    "message": self.translations["NSLOOKUP_EXECUTION_ERROR"],
                    "details": str(e),
                }
            )

    def start(self):
        self.started.emit()
        self.logger.info(
            self.__nslookup(
                self.url,
                self.nslookup_dns_server,
                self.nslookup_enable_tcp,
                self.nslookup_enable_tcp,
            )
        )
        self.finished.emit()


class TaskNslookup(Task):
    def __init__(self, logger, progress_bar=None, status_bar=None, parent=None):
        super().__init__(logger, progress_bar, status_bar, parent)

        self.translations = load_translations()

        self.label = self.translations["NSLOOKUP"]

        self.worker_thread = QThread()
        self.worker = NslookupWorker()
        self.worker.moveToThread(self.worker_thread)
        self.worker_thread.started.connect(self.worker.start)
        self.worker.started.connect(self.__started)
        self.worker.finished.connect(self.__finished)

        self.worker.error.connect(self.__handle_error)

        self.destroyed.connect(lambda: self.__destroyed_handler(self.__dict__))

    def __handle_error(self, error):
        self.update_task(State.COMPLETED, Status.FAILURE, error.get("details"))
        self.finished.emit()

        loop = QEventLoop()
        QTimer.singleShot(1000, loop.quit)
        loop.exec()

        self.worker_thread.quit()
        self.worker_thread.wait()

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
        self.worker.set_options(self.options)
        self.update_task(State.STARTED, Status.PENDING)
        self.set_message_on_the_statusbar(self.translations["NSLOOKUP_STARTED"])

        self.worker_thread.start()

    def __started(self):
        self.update_task(State.STARTED, Status.SUCCESS)
        self.started.emit()

    def __finished(self):
        self.logger.info(
            self.translations["NSLOOKUP_GET_INFO_URL"].format(self.options["url"])
        )
        self.set_message_on_the_statusbar(self.translations["NSLOOKUP_COMPLETED"])
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
