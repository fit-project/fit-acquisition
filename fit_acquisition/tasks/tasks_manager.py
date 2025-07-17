#!/usr/bin/env python3
# -*- coding:utf-8 -*-
######
# -----
# Copyright (c) 2023 FIT-Project
# SPDX-License-Identifier: GPL-3.0-only
# -----
######

import pkgutil
import sys
from importlib import import_module
from inspect import getmembers, isclass

from fit_configurations.controller.tabs.network.network_tool import (
    NetworkToolController,
)
from fit_configurations.controller.tabs.packet_capture.packet_capture import (
    PacketCaptureController,
)
from fit_configurations.controller.tabs.pec.pec import PecController
from fit_configurations.controller.tabs.screen_recorder.screen_recorder import (
    ScreenRecorderController,
)
from fit_configurations.controller.tabs.timestamp.timestamp import TimestampController
from PySide6.QtCore import QObject, Signal

from fit_acquisition import class_names
from fit_acquisition.tasks.tasks_handler import TasksHandler


class TasksManager(QObject):
    all_task_list_completed = Signal()

    def __init__(self):
        super().__init__()
        self.class_names_modules = dict()
        self.task_handler = TasksHandler()

        self.task_package_names = list()

    def register_task_package(self, package_name: str):
        if isinstance(package_name, str):
            self.task_package_names.append(package_name)

    def load_all_task_modules(self):
        for package_name in self.task_package_names:
            self.__load_task_modules_from_package(package_name)

    def __load_task_modules_from_package(self, package_name: str):
        try:
            package = import_module(package_name)
        except ModuleNotFoundError:
            return

        for importer, modname, ispkg in pkgutil.walk_packages(
            path=package.__path__, prefix=package.__name__ + ".", onerror=lambda x: None
        ):
            if modname not in sys.modules and not ispkg:
                import_module(modname)

            if modname in sys.modules and not ispkg:
                module = sys.modules[modname]

                for name, obj in getmembers(module, isclass):
                    if getattr(obj, "__is_task__", False) and bool(
                        self.is_enabled_tasks(name)
                    ):
                        self.class_names_modules.setdefault(name, []).append(module)

    def is_enabled_tasks(self, tasks):
        if isinstance(tasks, str):
            tasks = self.__remove_disable_tasks([tasks])
        elif isinstance(tasks, list):
            tasks = self.__remove_disable_tasks(tasks)

        return tasks

    def __remove_disable_tasks(self, tasks):
        _tasks = tasks.copy()
        for task in tasks:
            if (
                task == class_names.PACKETCAPTURE
                and PacketCaptureController().configuration["enabled"] is False
                or task == class_names.SCREENRECORDER
                and ScreenRecorderController().configuration["enabled"] is False
                or task == class_names.TIMESTAMP
                and TimestampController().configuration["enabled"] is False
                or task == class_names.PEC_AND_DOWNLOAD_EML
                and PecController().configuration["enabled"] is False
                or task == class_names.SSLKEYLOG
                and NetworkToolController().configuration["ssl_keylog"] is False
                or task == class_names.SSLCERTIFICATE
                and NetworkToolController().configuration["ssl_certificate"] is False
                or task == class_names.HEADERS
                and NetworkToolController().configuration["headers"] is False
                or task == class_names.WHOIS
                and NetworkToolController().configuration["whois"] is False
                or task == class_names.NSLOOKUP
                and NetworkToolController().configuration["nslookup"] is False
                or task == class_names.TRACEROUTE
                and NetworkToolController().configuration["traceroute"] is False
            ):
                _tasks.remove(task)

        return _tasks

    def init_tasks(self, task_list, logger, progress_bar, status_bar):
        for key in self.class_names_modules.keys():
            if key in task_list:
                value = self.class_names_modules.get(key)[0]
                task = getattr(value, key)
                task = task(logger, progress_bar, status_bar)

    def get_tasks(self):
        return self.task_handler.get_tasks()

    def get_task(self, name):
        return self.task_handler.get_task(name)

    def clear_tasks(self):
        self.task_handler.clear_tasks()

    def get_task_by_class_name(self, name):
        return self.task_handler.get_task(name)

    def get_tasks_from_class_name(self, names):
        tasks = []
        for name in names:
            task = self.get_task_by_class_name(name)
            if task:
                tasks.append(task)
        return tasks

    def are_task_names_in_the_same_state(self, tasks, state):
        return self.task_handler.are_task_names_in_the_same_state(tasks, state)
