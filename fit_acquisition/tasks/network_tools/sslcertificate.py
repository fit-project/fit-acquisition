#!/usr/bin/env python3
# -*- coding:utf-8 -*-
######
# -----
# Copyright (c) 2023 FIT-Project
# SPDX-License-Identifier: GPL-3.0-only
# -----
######

import os
import socket
import ssl
from urllib.parse import urlparse

from fit_common.gui.utils import Status

from fit_acquisition.tasks.task import Task
from fit_acquisition.tasks.task_worker import TaskWorker


class SSLCertificateWorker(TaskWorker):

    def __check_if_peer_certificate_exist(self, url):
        parsed_url = urlparse(url)
        if not parsed_url.netloc:
            raise ValueError(self.translations["MALFORMED_URL_ERROR"])

        host = parsed_url.hostname
        port = parsed_url.port or 443

        context = ssl.create_default_context()
        with socket.create_connection((host, port), timeout=10) as sock:
            with context.wrap_socket(sock, server_hostname=host) as ssock:
                cert = ssock.getpeercert()
                return bool(cert)

    def __get_peer_PEM_cert(self, url, port=443, timeout=10):
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

        if not der_cert:
            raise ValueError("Empty certificate received")

        return ssl.DER_cert_to_PEM_cert(der_cert)

    def __save_PEM_cert_to_CER_cert(self, filename, certificate):
        with open(filename, "w") as cer_file:
            cer_file.write(certificate)

    def start(self):
        self.started.emit()
        try:
            is_peer_certificate_exist = self.__check_if_peer_certificate_exist(
                self.options["url"]
            )

            if is_peer_certificate_exist:
                certificate = self.__get_peer_PEM_cert(self.options["url"])
                self.__save_PEM_cert_to_CER_cert(
                    os.path.join(self.options["acquisition_directory"], "server.cer"),
                    certificate,
                )

            self.finished.emit()

        except ValueError as e:
            self.error.emit(
                {
                    "title": self.translations["SSLCERTIFICATE_ERROR_TITLE"],
                    "message": str(e),
                    "details": str(e),
                }
            )
        except (socket.error, ssl.SSLError) as e:
            self.error.emit(
                {
                    "title": self.translations["SSLCERTIFICATE_ERROR_TITLE"],
                    "message": self.translations["SSLCERTIFICATE_CONNECTION_ERROR"],
                    "details": str(e),
                }
            )
        except (OSError, IOError) as e:
            self.error.emit(
                {
                    "title": self.translations["SSLCERTIFICATE_ERROR_TITLE"],
                    "message": self.translations[
                        "SSLCERTIFICATE_SAVING_CERTIFICATE_ERROR"
                    ],
                    "details": str(e),
                }
            )
        except Exception as e:
            self.error.emit(
                {
                    "title": self.translations["SSLCERTIFICATE_ERROR_TITLE"],
                    "message": self.translations["SSLCERTIFICATE_ERROR_CHECK"],
                    "details": str(e),
                }
            )


class TaskSSLCertificate(Task):
    def __init__(self, logger, progress_bar=None, status_bar=None):
        super().__init__(
            logger,
            progress_bar,
            status_bar,
            label="SSLCERTIFICATE",
            worker_class=SSLCertificateWorker,
        )

    def start(self):
        super().start_task(self.translations["SSLCERTIFICATE_STARTED"])

    def _finished(self, status=Status.SUCCESS, details=""):
        if status == Status.SUCCESS:
            details = self.translations["SSLCERTIFICATE_COMPLETED"]

        message = self.translations["SSLCERTIFICATE_GET_FROM_URL"].format(
            status.name, self.options["url"]
        )

        super()._finished(status, details, message)
