#!/usr/bin/env python3
# -*- coding:utf-8 -*-
######
# -----
# Copyright (c) 2023 FIT-Project
# SPDX-License-Identifier: GPL-3.0-only
# -----
######

import os
import pwd
import subprocess
import threading

from fit_common.core import debug, get_context, log_exception
from fit_common.gui.utils import Status
from fit_configurations.controller.tabs.screen_recorder.screen_recorder import (
    ScreenRecorderController,
)
from PySide6.QtWidgets import QApplication

from fit_acquisition.tasks.task import Task
from fit_acquisition.tasks.task_worker import TaskWorker


class ScreenRecorderWorker(TaskWorker):
    def __init__(self):
        super().__init__()

        self.__binary_path = None
        self.__filename = ""
        self.__is_enabled_audio_recording = False
        self.__process = None
        self.__stdout_thread = None
        self.__stderr_thread = None
        self.__wait_thread = None
        self.__stop_requested = False
        self.__started_emitted = False
        self.__stderr_lines = []
        self.__lock = threading.RLock()

        self.destroyed.connect(self.stop)

    @TaskWorker.options.setter
    def options(self, options):
        self._options = options
        self.__acquisition_directory = options["acquisition_directory"]
        self.__filename = os.path.join(
            self.__acquisition_directory, options["filename"] + ".mp4"
        )

        self.__is_enabled_audio_recording = ScreenRecorderController().configuration[
            "enabled_audio"
        ]

    def start(self):
        try:
            with self.__lock:
                if self.__process and self.__process.poll() is None:
                    raise RuntimeError("screen recorder process is already running")

                self.__binary_path = os.environ.get("FIT_SCREEN_RECODER_PATH")
                if not self.__binary_path:
                    raise FileNotFoundError(
                        "FIT_SCREEN_RECODER_PATH is not set. Export the full path to "
                        "fit-screen-recorder before running the screen recorder."
                    )

                popen_kwargs = self.__build_popen_kwargs()
                command = [
                    self.__binary_path,
                    "--output",
                    self.__filename,
                    "--stdin-control",
                ]
                display_id = self.__resolve_display_id(popen_kwargs)
                if display_id is not None:
                    command.extend(["--display-id", str(display_id)])

                if not self.__is_enabled_audio_recording:
                    command.append("--no-audio")

                self.__stop_requested = False
                self.__started_emitted = False
                self.__stderr_lines = []
                debug(
                    "screen recorder command",
                    command,
                    context=get_context(self),
                )
                self.__process = subprocess.Popen(
                    command,
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    bufsize=1,
                    **popen_kwargs,
                )

                self.__stdout_thread = threading.Thread(
                    target=self.__read_stdout,
                    args=(self.__process,),
                    daemon=True,
                )
                self.__stderr_thread = threading.Thread(
                    target=self.__read_stderr,
                    args=(self.__process,),
                    daemon=True,
                )
                self.__wait_thread = threading.Thread(
                    target=self.__wait_for_process,
                    args=(self.__process,),
                    daemon=True,
                )

                self.__stdout_thread.start()
                self.__stderr_thread.start()
                self.__wait_thread.start()
        except Exception as e:
            log_exception(e, context=get_context(self))
            debug(
                "Start screen recorder failed",
                str(e),
                context=get_context(self),
            )
            self.__emit_error(str(e))

    def __resolve_display_id(self, popen_kwargs):
        displays = self.__list_displays(popen_kwargs)
        if len(displays) <= 1:
            return None

        app = QApplication.instance()
        if app is None:
            return None

        screen = app.screenAt(self._options["window_pos"])
        if screen is None:
            return None

        geometry = screen.geometry()
        for display in displays:
            if (
                display.get("origin_x") == geometry.x()
                and display.get("origin_y") == geometry.y()
                and display.get("width") == geometry.width()
                and display.get("height") == geometry.height()
            ):
                return display.get("id")

        return None

    def __list_displays(self, popen_kwargs):
        process = subprocess.run(
            [self.__binary_path, "--list-displays"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True,
            **popen_kwargs,
        )

        entries = {}
        for raw_line in process.stdout.splitlines():
            line = raw_line.strip()
            if not line or "=" not in line:
                continue

            key, value = line.split("=", 1)
            entries[key] = value

        display_count = int(entries.get("display_count", "0"))
        displays = []
        for index in range(display_count):
            prefix = f"display.{index}."
            display_id = entries.get(f"{prefix}id")
            if display_id is None:
                continue

            displays.append(
                {
                    "id": int(display_id),
                    "origin_x": int(entries.get(f"{prefix}origin_x", "0")),
                    "origin_y": int(entries.get(f"{prefix}origin_y", "0")),
                    "width": int(entries.get(f"{prefix}width", "0")),
                    "height": int(entries.get(f"{prefix}height", "0")),
                }
            )

        debug(
            "screen recorder displays",
            displays,
            context=get_context(self),
        )
        return displays

    def __build_popen_kwargs(self):
        sudo_user = os.environ.get("SUDO_USER")
        if os.geteuid() != 0 or not sudo_user:
            return {}

        user_info = pwd.getpwnam(sudo_user)
        child_env = os.environ.copy()
        child_env["HOME"] = user_info.pw_dir
        child_env["USER"] = sudo_user
        child_env["LOGNAME"] = sudo_user

        def demote():
            os.initgroups(sudo_user, user_info.pw_gid)
            os.setgid(user_info.pw_gid)
            os.setuid(user_info.pw_uid)

        debug(
            f"Launching fit-screen-recorder as user {sudo_user}",
            context=get_context(self),
        )
        return {
            "env": child_env,
            "preexec_fn": demote,
        }

    def stop(self):
        try:
            with self.__lock:
                process = self.__process
                if not process or process.poll() is not None:
                    return

                self.__stop_requested = True
                stdin = process.stdin

            if stdin:
                try:
                    stdin.write("stop\n")
                    stdin.flush()
                except BrokenPipeError:
                    debug(
                        "Screen recorder stdin already closed",
                        context=get_context(self),
                    )
            else:
                process.terminate()

            threading.Thread(
                target=self.__enforce_stop_timeout,
                args=(process,),
                daemon=True,
            ).start()
        except Exception as e:
            log_exception(e, context=get_context(self))
            debug(
                "Stop screen recorder failed",
                str(e),
                context=get_context(self),
            )
            self.__emit_error(str(e))

    def __read_stdout(self, process):
        stdout = process.stdout
        if stdout is None:
            return

        try:
            for line in stdout:
                stripped_line = line.strip()
                if stripped_line:
                    debug(
                        "fit-screen-recorder stdout",
                        stripped_line,
                        context=get_context(self),
                    )

                if stripped_line == "runner=ready":
                    with self.__lock:
                        if self.__process is process and not self.__started_emitted:
                            self.__started_emitted = True
                            self.started.emit()
        except Exception as e:
            log_exception(e, context=get_context(self))
            debug(
                "Read screen recorder stdout failed",
                str(e),
                context=get_context(self),
            )

    def __read_stderr(self, process):
        stderr = process.stderr
        if stderr is None:
            return

        try:
            for line in stderr:
                stripped_line = line.strip()
                if not stripped_line:
                    continue

                with self.__lock:
                    if self.__process is process:
                        self.__stderr_lines.append(stripped_line)
                        self.__stderr_lines = self.__stderr_lines[-20:]

                debug(
                    "fit-screen-recorder stderr",
                    stripped_line,
                    context=get_context(self),
                )
        except Exception as e:
            log_exception(e, context=get_context(self))
            debug(
                "Read screen recorder stderr failed",
                str(e),
                context=get_context(self),
            )

    def __wait_for_process(self, process):
        try:
            return_code = process.wait()
        except Exception as e:
            log_exception(e, context=get_context(self))
            debug(
                "Wait screen recorder process failed",
                str(e),
                context=get_context(self),
            )
            self.__emit_error(str(e))
            return

        with self.__lock:
            if self.__process is not process:
                return

            stop_requested = self.__stop_requested
            started_emitted = self.__started_emitted
            stderr_details = "\n".join(self.__stderr_lines).strip()
            self.__process = None

        if return_code == 0:
            if stop_requested:
                self.finished.emit()
                return

            if started_emitted:
                self.__emit_error("fit-screen-recorder terminated unexpectedly")
                return

            self.__emit_error(
                "fit-screen-recorder terminated before reporting readiness"
            )
            return

        details = (
            stderr_details or f"fit-screen-recorder exited with code {return_code}"
        )
        self.__emit_error(details)

    def __enforce_stop_timeout(self, process):
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            debug(
                "Screen recorder stop timeout reached, terminating process",
                context=get_context(self),
            )
            process.terminate()
            try:
                process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                debug(
                    "Screen recorder terminate timeout reached, killing process",
                    context=get_context(self),
                )
                process.kill()

    def __emit_error(self, details):
        self.error.emit(
            {
                "title": self.translations["SCREEN_RECORDER_ERROR_TITLE"],
                "message": self.translations["SCREEN_RECORDER_ERROR_MSG"],
                "details": details,
            }
        )


class TaskScreenRecorder(Task):
    def __init__(self, logger, progress_bar=None, status_bar=None):
        super().__init__(
            logger,
            progress_bar,
            status_bar,
            label="SCREEN_RECORDER",
            is_infinite_loop=True,
            worker_class=ScreenRecorderWorker,
        )

    @Task.options.setter
    def options(self, options):
        options["filename"] = os.path.join(
            options["acquisition_directory"],
            ScreenRecorderController().configuration["filename"],
        )
        self._options = options

    def start(self):
        super().start_task(self.translations["SCREEN_RECORDER_STARTED"])

    def stop(self):
        super().stop_task(self.translations["SCREEN_RECORDER_STOPPED"])

    def _started(self):
        super()._started(self.translations["SCREEN_RECORDER_STARTED_DETAILS"])

    def _finished(self, status=Status.SUCCESS, details=""):
        if status == Status.SUCCESS:
            details = self.translations["NETWORK_PACKET_CAPTURE_COMPLETED_DETAILS"]

        super()._finished(
            status,
            details,
            self.translations["SCREEN_RECORDER_COMPLETED"].format(status.name),
        )
