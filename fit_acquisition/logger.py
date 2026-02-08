#!/usr/bin/env python3
# -*- coding:utf-8 -*-
######
# -----
# Copyright (c) 2023 FIT-Project
# SPDX-License-Identifier: GPL-3.0-only
# -----
######

import datetime
import logging
import os

from fit_configurations.controller.tabs.network.network_tool import (
    NetworkToolController,
)

from fit_acquisition.logger_names import LoggerName

# Produce RFC 3339 timestamps
logging.Formatter.formatTime = (
    lambda self, record, datefmt: datetime.datetime.fromtimestamp(
        record.created, datetime.timezone.utc
    )
    .astimezone()
    .isoformat()
)


class LogConfigTools:
    def __init__(self):
        self.config = {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "detailed": {
                    "class": "logging.Formatter",
                    "format": "%(asctime)s %(name)-15s %(levelname)-8s %(processName)-10s %(message)s",
                },
                "hashreport": {"class": "logging.Formatter", "format": "%(message)s"},
                "acquisition": {
                    "class": "logging.Formatter",
                    "format": "%(asctime)s - %(message)s",
                },
            },
            "handlers": {
                "null": {"class": "logging.NullHandler"},
                "facquisition": {
                    "class": "logging.FileHandler",
                    "filename": "acquisition.log",
                    "mode": "w",
                    "formatter": "acquisition",
                },
                "fhashreport": {
                    "class": "logging.FileHandler",
                    "filename": "acquisition.hash",
                    "mode": "w",
                    "formatter": "hashreport",
                },
            },
            "loggers": {
                LoggerName.SCRAPER_WEB.value: {
                    "handlers": ["facquisition"],
                    "level": "INFO",
                },
                LoggerName.SCRAPER_MAIL.value: {
                    "handlers": ["facquisition"],
                    "level": "INFO",
                },
                LoggerName.SCRAPER_INSTAGRAM.value: {
                    "handlers": ["facquisition"],
                    "level": "INFO",
                },
                LoggerName.SCRAPER_VIDEO.value: {
                    "handlers": ["facquisition"],
                    "level": "INFO",
                },
                LoggerName.SCRAPER_ENTIRE_WEBSITE.value: {
                    "handlers": ["facquisition"],
                    "level": "INFO",
                },
                LoggerName.HASHREPORT.value: {
                    "handlers": ["fhashreport"],
                    "level": "INFO",
                },
            },
            "root": {"handlers": ["null"], "propagate": False},
        }

    def change_filehandlers_path(self, path, exclude=None):
        for key in self.config["handlers"]:
            handler = self.config["handlers"][key]
            if "filename" in handler.keys():
                stripped = handler["filename"].split("\\")[-1]
                if stripped:
                    handler["filename"] = os.path.join(path, stripped)
                else:
                    handler["filename"] = os.path.join(path, handler["filename"])

    def disable_loggers(self, loggers):
        for logger in loggers:
            for handler in logger.handlers.copy():
                logger.removeHandler(handler)
            logger.addHandler(logging.NullHandler())
            logger.propagate = False

    def set_dynamic_loggers(self):
        # ENABLE/DISABLE WHOIS
        if NetworkToolController().configuration["whois"]:
            self.config["formatters"]["whois"] = {
                "class": "logging.Formatter",
                "format": "%(message)s",
            }
            self.config["handlers"]["fwhois"] = {
                "class": "logging.FileHandler",
                "filename": "whois.txt",
                "mode": "w",
                "formatter": "whois",
            }
            self.config["loggers"]["whois"] = {"handlers": ["fwhois"], "level": "INFO"}
        else:
            if "whois" in self.config["formatters"]:
                self.config["formatters"].pop("whois")
            if "fwhois" in self.config["handlers"]:
                self.config["handlers"].pop("fwhois")
            if "whois" in self.config["loggers"]:
                self.config["loggers"].pop("whois")

        # ENABLE/DISABLE HEADERS
        if NetworkToolController().configuration["headers"]:
            self.config["formatters"]["headers"] = {
                "class": "logging.Formatter",
                "format": "%(message)s",
            }
            self.config["handlers"]["fheaders"] = {
                "class": "logging.FileHandler",
                "filename": "headers.txt",
                "mode": "w",
                "formatter": "headers",
            }
            self.config["loggers"]["headers"] = {
                "handlers": ["fheaders"],
                "level": "INFO",
            }
        else:
            if "headers" in self.config["formatters"]:
                self.config["formatters"].pop("headers")
            if "fheaders" in self.config["handlers"]:
                self.config["handlers"].pop("fheaders")
            if "headers" in self.config["loggers"]:
                self.config["loggers"].pop("headers")

        # ENABLE/DISABLE NSLOOKUP
        if NetworkToolController().configuration["nslookup"]:
            self.config["formatters"]["nslookup"] = {
                "class": "logging.Formatter",
                "format": "%(message)s",
            }
            self.config["handlers"]["fnslookup"] = {
                "class": "logging.FileHandler",
                "filename": "nslookup.txt",
                "mode": "w",
                "formatter": "nslookup",
            }
            self.config["loggers"]["nslookup"] = {
                "handlers": ["fnslookup"],
                "level": "INFO",
            }
        else:
            if "nslookup" in self.config["formatters"]:
                self.config["formatters"].pop("nslookup")
            if "fnslookup" in self.config["handlers"]:
                self.config["handlers"].pop("fnslookup")
            if "nslookup" in self.config["loggers"]:
                self.config["loggers"].pop("nslookup")
