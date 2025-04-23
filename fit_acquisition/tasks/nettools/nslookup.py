#!/usr/bin/env python3
# -*- coding:utf-8 -*-
######
# -----
# Copyright (c) 2023 FIT-Project
# SPDX-License-Identifier: GPL-3.0-only
# -----
######
import logging
from PyQt6.QtCore import QObject, pyqtSignal, QThread
from common.constants.view.tasks import labels, state, status

from controller.configurations.tabs.network.networkcheck import (
    NetworkControllerCheck as NetworkCheckController,
)

from common.utility import nslookup
from common.constants import logger

from view.tasks.task import Task


class NslookupWorker(QObject):
    logger = logging.getLogger("nslookup")
    finished = pyqtSignal()
    started = pyqtSignal()

    def set_options(self, options):
        self.url = options["url"]
        self.nslookup_dns_server = options["nslookup_dns_server"]
        self.nslookup_enable_tcp = options["nslookup_enable_tcp"]
        self.nslookup_enable_verbose_mode = options["nslookup_enable_verbose_mode"]

    def start(self):
        self.started.emit()
        self.logger.info(
            nslookup(
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

        self.label = labels.NSLOOKUP

        self.worker_thread = QThread()
        self.worker = NslookupWorker()
        self.worker.moveToThread(self.worker_thread)
        self.worker_thread.started.connect(self.worker.start)
        self.worker.started.connect(self.__started)
        self.worker.finished.connect(self.__finished)

        self.destroyed.connect(lambda: self.__destroyed_handler(self.__dict__))

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
        self.update_task(state.STARTED, status.PENDING)
        self.set_message_on_the_statusbar(logger.NSLOOKUP_STARTED)

        self.worker_thread.start()

    def __started(self):
        self.update_task(state.STARTED, status.SUCCESS)
        self.started.emit()

    def __finished(self):
        self.logger.info(logger.NSLOOKUP_GET_INFO_URL.format(self.options["url"]))
        self.set_message_on_the_statusbar(logger.NSLOOKUP_COMPLETED)
        self.upadate_progress_bar()

        self.update_task(state.COMPLETED, status.SUCCESS)

        self.finished.emit()

        self.worker_thread.quit()
        self.worker_thread.wait()

    def __destroyed_handler(self, _dict):
        if self.worker_thread.isRunning():
            self.worker_thread.quit()
            self.worker_thread.wait()
