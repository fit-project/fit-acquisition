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
from whois import NICClient, extract_domain, IPV4_OR_V6
from shiboken6 import isValid

from PySide6.QtCore import QObject, Signal, QThread, QEventLoop, QTimer
from PySide6.QtWidgets import QMessageBox

from fit_acquisition.task import Task
from fit_common.gui.utils import State, Status
from fit_common.gui.error import Error as ErrorView
from fit_acquisition.lang import load_translations


class WhoisWorker(QObject):
    logger = logging.getLogger("whois")
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

    def __whois(self, url, flags=0):
        try:
            ip_match = IPV4_OR_V6.match(url)
            if ip_match:
                domain = url
                try:
                    result = socket.gethostbyaddr(url)
                    domain = extract_domain(result[0])
                except socket.herror as e:
                    self.error.emit(
                        {
                            "title": self.translations["WHOIS_ERROR_TITLE"],
                            "message": self.translations["WHOIS_DNS_RESOLUTON_ERROR"],
                            "details": str(e),
                        }
                    )
                    return
            else:
                domain = extract_domain(url)

            if not domain:
                self.error.emit(
                    {
                        "title": self.translations["WHOIS_ERROR_TITLE"],
                        "message": self.translations["WHOIS_INVALID_DOMAIN_ERROR"],
                        "details": "",
                    }
                )
                return

            # WHOIS client
            nic_client = NICClient()

            return nic_client.whois_lookup(None, domain.encode("idna"), flags)

        except Exception as e:
            self.error.emit(
                {
                    "title": self.translations["WHOIS_ERROR_TITLE"],
                    "message": self.translations["WHOIS_EXECUTION_ERROR"],
                    "details": str(e),
                }
            )
            return

    def start(self):
        self.started.emit()
        self.logger.info(self.__whois(self.url))
        self.finished.emit()


class TaskWhois(Task):
    def __init__(self, logger, progress_bar=None, status_bar=None, parent=None):
        super().__init__(logger, progress_bar, status_bar, parent)

        self.translations = load_translations()

        self.label = self.translations["WHOIS"]

        self.worker_thread = QThread()
        self.worker = WhoisWorker()
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
        self.set_message_on_the_statusbar(self.translations["WHOIS_STARTED"])
        self.worker.url = self.options["url"]
        self.worker_thread.start()

    def __started(self):
        self.update_task(State.STARTED, Status.SUCCESS)
        self.started.emit()

    def __finished(self):
        self.logger.info(
            self.translations["WHOIS_GET_INFO_URL"].format(self.options["url"])
        )
        self.set_message_on_the_statusbar(self.translations["WHOIS_COMPLETED"])
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
