#!/usr/bin/env python3
# -*- coding:utf-8 -*-
######
# -----
# Copyright (c) 2023 FIT-Project
# SPDX-License-Identifier: GPL-3.0-only
# -----
######

from PySide6.QtCore import QObject, Signal


class TasksHandler(QObject):
    all_tasks_completed = Signal()

    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not hasattr(self, "_initialized"):
            super().__init__()
            self.__tasks = []
            self._initialized = True

    def add_task(self, task):
        self.__tasks.append(task)

    def get_tasks(self):
        return self.__tasks

    def get_task(self, name):
        return next(
            (task for task in self.__tasks if task.__class__.__name__ == name), None
        )

    def clear_tasks(self):
        self.__tasks = list()

    def are_task_names_in_the_same_state(self, names, state):
        are_completed = False
        __state = list()

        for name in names:
            task = self.get_task(name)
            if task:
                __state.append(task.state)

        if __state:
            __state = list(set(__state))
            if len(__state) == 1 and __state[0] == state:
                are_completed = True

        return are_completed
