#!/usr/bin/env python3
# -*- coding:utf-8 -*-
######
# -----
# Copyright (c) 2023 FIT-Project
# SPDX-License-Identifier: GPL-3.0-only
# -----
######


class ClassNames:
    def __init__(self):
        self._names = {
            # ACQUISITION TASKS
            "PACKETCAPTURE": "TaskPacketCapture",
            "SCREENRECORDER": "TaskScreenRecorder",
            # NETWORK TOOLS TASKS
            "NSLOOKUP": "TaskNslookup",
            "WHOIS": "TaskWhois",
            "HEADERS": "TaskHeaders",
            "TRACEROUTE": "TaskTraceroute",
            "SSLKEYLOG": "TaskSSLKeyLog",
            "SSLCERTIFICATE": "TaskSSLCertificate",
            # POST ACQUISITION TASKS
            "HASH": "TaskHash",
            "REPORT": "TaskReport",
            "TIMESTAMP": "TaskTimestamp",
            "PEC_AND_DOWNLOAD_EML": "TaskPecAndDownloadEml",
            "ZIP_AND_REMOVE_FOLDER": "TaskZipAndRemoveFolder",
            "SAVE_CASE_INFO": "TaskSaveCaseInfo",
        }

    def register(self, name: str, value: str):
        self._names[name] = value

    def get(self, name: str) -> str:
        return self._names.get(name)

    def list_all(self) -> dict:
        return dict(self._names)

    def __getattr__(self, name: str) -> str:
        try:
            return self._names[name]
        except KeyError:
            raise AttributeError(f"'ClassNames' object has no attribute '{name}'")

    def __contains__(self, name: str) -> bool:
        return name in self._names


class_names = ClassNames()
