#!/usr/bin/env python3
# -*- coding:utf-8 -*-
######
# -----
# Copyright (c) 2023 FIT-Project
# SPDX-License-Identifier: GPL-3.0-only
# -----
######

import os
import sys
import requests
import ssl
import socket

from urllib.parse import urlparse
from shiboken6 import isValid


from PySide6.QtCore import QObject, Signal, QThread, QEventLoop, QTimer
from PySide6.QtWidgets import QMessageBox

from fit_acquisition.task import Task
from fit_common.gui.utils import State, Status
from fit_common.gui.error import Error as ErrorView
from fit_acquisition.lang import load_translations


class SSLCertificateWorker(QObject):
    finished = Signal(bool)
    started = Signal()
    error = Signal(object)

    def __init__(self, parent=None):
        QObject.__init__(self, parent=parent)
        self.translations = load_translations()

    def set_options(self, options):
        self.url = options["url"]
        self.folder = options["acquisition_directory"]

    def __check_if_peer_certificate_exist(self, url):
        try:
            parsed_url = urlparse(url)
            if not parsed_url.netloc:
                self.error.emit(
                    {
                        "title": self.translations["SSLCERTIFICATE_ERROR_TITLE"],
                        "message": self.translations["MALFORMED_URL_ERROR"],
                        "details": "",
                    }
                )
                return False

            host = parsed_url.hostname
            port = parsed_url.port or 443

            context = ssl.create_default_context()
            with socket.create_connection((host, port), timeout=10) as sock:
                with context.wrap_socket(sock, server_hostname=host) as ssock:
                    cert = ssock.getpeercert()

                    if cert:
                        return True
                    else:
                        return False

        except (socket.error, ssl.SSLError) as e:
            self.error.emit(
                {
                    "title": self.translations["SSLCERTIFICATE_ERROR_TITLE"],
                    "message": self.translations["HTTP_CONNECTION_ERROR"],
                    "details": str(e),
                }
            )
            return False
        except Exception as e:
            self.error.emit(
                {
                    "title": self.translations["SSLCERTIFICATE_ERROR_TITLE"],
                    "message": self.translations["SSLCERTIFICATE_ERROR_CHECK"],
                    "details": str(e),
                }
            )
            return False

    def __get_peer_PEM_cert(self, url, port=443, timeout=10):
        try:
            parsed_url = urlparse(url)
            netloc = parsed_url.netloc

            if not netloc:
                raise ValueError(self.translations["MALFORMED_URL_ERROR"])

            if ":" in netloc:
                netloc, port = netloc.split(":")
                port = int(port)

            context = ssl.create_default_context()
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE

            conn = socket.create_connection((netloc, port), timeout=timeout)
            sock = context.wrap_socket(conn, server_hostname=netloc)

            try:
                der_cert = sock.getpeercert(True)
            finally:
                sock.close()

            if der_cert:
                return ssl.DER_cert_to_PEM_cert(der_cert)
            else:
                return None

        except (socket.error, ssl.SSLError, ValueError) as e:
            self.error.emit(
                {
                    "title": self.translations["SSLCERTIFICATE_ERROR_TITLE"],
                    "message": self.translations["SSLCERTIFICATE_CONNECTION_ERROR"],
                    "details": str(e),
                }
            )
            return None

    def __save_PEM_cert_to_CER_cert(self, filename, certificate):
        try:
            with open(filename, "w") as cer_file:
                cer_file.write(certificate)
            return True
        except (OSError, IOError) as e:
            {
                "title": self.translations["SSLCERTIFICATE_ERROR_TITLE"],
                "message": self.translations["SSLCERTIFICATE_SAVING_CERTIFICATE_ERROR"],
                "details": str(e),
            }
            return False

    def start(self):
        self.started.emit()
        is_peer_certificate_exist = self.__check_if_peer_certificate_exist(self.url)
        if is_peer_certificate_exist:
            certificate = self.__get_peer_PEM_cert(self.url)
            if certificate is not None:
                self.__save_PEM_cert_to_CER_cert(
                    os.path.join(self.folder, "server.cer"), certificate
                )

        self.finished.emit(is_peer_certificate_exist)


class TaskSSLCertificate(Task):
    def __init__(self, logger, progress_bar=None, status_bar=None, parent=None):
        super().__init__(logger, progress_bar, status_bar, parent)

        self.translations = load_translations()

        self.label = self.translations["SSLCERTIFICATE"]

        self.worker_thread = QThread()
        self.worker = SSLCertificateWorker()
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
        self.worker.set_options(self.options)
        self.update_task(State.STARTED, Status.PENDING)
        self.set_message_on_the_statusbar(self.translations["SSLCERTIFICATE_STARTED"])
        self.worker_thread.start()

    def __started(self):
        self.update_task(State.STARTED, Status.SUCCESS)
        self.started.emit()

    def __finished(self, is_peer_certificate_exist):
        msg = self.translations["SSLCERTIFICATE_GET_FROM_URL"].format(
            self.options["url"]
        )
        if is_peer_certificate_exist is False:
            msg = self.translations["SSLCERTIFICATE_NOT_EXIST"].format(
                self.options["url"]
            )
            self.details = msg

        self.logger.info(msg)
        self.set_message_on_the_statusbar(self.translations["SSLCERTIFICATE_COMPLETED"])
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
