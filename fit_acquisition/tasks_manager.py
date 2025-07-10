#!/usr/bin/env python3
# -*- coding:utf-8 -*-
######
# -----
# Copyright (c) 2023 FIT-Project
# SPDX-License-Identifier: GPL-3.0-only
# -----
######

from PySide6.QtCore import QObject, Signal
import pkgutil
import sys
from inspect import isclass
from importlib import import_module

from fit_acquisition.tasks_handler import TasksHandler
from fit_acquisition import class_names
from fit_configurations.controller.tabs.packetcapture.packetcapture import (
    PacketCapture as PacketCaptureCotroller,
)
from fit_configurations.controller.tabs.screenrecorder.screenrecorder import (
    ScreenRecorder as ScreenRecorderConfigurationController,
)
from fit_configurations.controller.tabs.timestamp.timestamp import (
    Timestamp as TimestampController,
)
from fit_configurations.controller.tabs.pec.pec import Pec as PecController
from fit_configurations.controller.tabs.network.networktools import (
    NetworkTools as NetworkToolsController,
)


class TasksManager(QObject):
    all_task_list_completed = Signal()

    def __init__(self):
        super().__init__()
        self.class_names_modules = dict()
        self.task_handler = TasksHandler()

        self.task_packages = list()

    def register_task_package(self, package):
        self.task_packages.append(package)

    def load_all_task_modules(self):
        for package in self.task_packages:
            self.__load_task_modules_from_package(package)

    def __load_task_modules_from_package(self, package):
        if isinstance(package, str):
            try:
                package = import_module(package)
            except ModuleNotFoundError:
                return

        for importer, modname, ispkg in pkgutil.walk_packages(
            path=package.__path__, prefix=package.__name__ + ".", onerror=lambda x: None
        ):
            if modname not in sys.modules and not ispkg:
                import_module(modname)

            if modname in sys.modules and not ispkg:
                class_name = class_names.__dict__.get(modname.rsplit(".", 1)[1].upper())
                if (
                    class_name
                    and isclass(getattr(sys.modules[modname], class_name, None))
                    and bool(self.is_enabled_tasks(class_name))
                ):
                    self.class_names_modules.setdefault(class_name, []).append(
                        sys.modules[modname]
                    )

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
                and PacketCaptureCotroller().options["enabled"] is False
                or task == class_names.SCREENRECORDER
                and ScreenRecorderConfigurationController().options["enabled"] is False
                or task == class_names.TIMESTAMP
                and TimestampController().options["enabled"] is False
                or task == class_names.PEC_AND_DOWNLOAD_EML
                and PecController().options["enabled"] is False
                or task == class_names.SSLKEYLOG
                and NetworkToolsController().configuration["ssl_keylog"] is False
                or task == class_names.SSLCERTIFICATE
                and NetworkToolsController().configuration["ssl_certificate"] is False
                or task == class_names.HEADERS
                and NetworkToolsController().configuration["headers"] is False
                or task == class_names.WHOIS
                and NetworkToolsController().configuration["whois"] is False
                or task == class_names.NSLOOKUP
                and NetworkToolsController().configuration["nslookup"] is False
                or task == class_names.TRACEROUTE
                and NetworkToolsController().configuration["traceroute"] is False
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
