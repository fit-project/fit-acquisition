#!/usr/bin/env python3
# -*- coding:utf-8 -*-
######
# -----
# Copyright (c) 2023 FIT-Project
# SPDX-License-Identifier: GPL-3.0-only
# -----
######

import os

from PySide6.QtCore import QThread, QUrl, QEventLoop, QTimer
from PySide6.QtWidgets import QApplication
from PySide6.QtMultimedia import (
    QMediaCaptureSession,
    QMediaRecorder,
    QScreenCapture,
    QAudioInput,
)


from fit_common.gui.utils import State, Status
from fit_common.gui.multimedia import get_vb_cable_virtual_audio_device

from fit_configurations.controller.tabs.screen_recorder.screen_recorder import ScreenRecorderController

from fit_acquisition.lang import load_translations
from fit_acquisition.tasks.task import Task
from fit_acquisition.tasks.task_worker import TaskWorker


class ScreenRecorderWorker(TaskWorker):
    def __init__(self):
        super().__init__()

        self.__is_enabled_audio_recording = False
        self.destroyed.connect(self.stop)

        # Video recording
        self.__video_to_record_session = QMediaCaptureSession()
        self.__screen_to_record = QScreenCapture()
        self.__video_to_record_session.setScreenCapture(self.__screen_to_record)
        self.__video_recorder = QMediaRecorder()
        self.__video_recorder.recorderStateChanged.connect(
            self.__video_recorder_state_handler
        )
        self.__video_to_record_session.setRecorder(self.__video_recorder)

    def __video_recorder_state_handler(self, recorder_state):
        if recorder_state == QMediaRecorder.RecorderState.StoppedState:
            self.__join_audio_and_video()

    @TaskWorker.options.setter
    def options(self, options):
        self._options = options
        self.__acquisition_directory = options["acquisition_directory"]
        self.__filename = options["filename"]

        app = QApplication.instance()
        screen = app.screenAt(options["window_pos"])
        if screen:
            self.__screen_to_record.setScreen(screen)

        if hasattr(app, "is_enabled_audio_recording"):
            self.__is_enabled_audio_recording = getattr(app, "is_enabled_audio_recording")

        if self.__is_enabled_audio_recording:
            self.__audio_path = os.path.join(self.__acquisition_directory, "screenrecorder/audio")
            self.__video_path = os.path.join(self.__acquisition_directory, "screenrecorder/video")
            self.__create_screen_recorder_directories()

            self.__video_recorder.setOutputLocation(
                QUrl.fromLocalFile(os.path.join(self.__video_path, "screenrecorder"))
            )

            self.__audio_capture_session = QMediaCaptureSession()
            self.__audio_input = QAudioInput(get_vb_cable_virtual_audio_device())
            self.__audio_capture_session.setAudioInput(self.__audio_input)
            self.__audio_recorder = QMediaRecorder()
            self.__audio_recorder.setOutputLocation(
                QUrl.fromLocalFile(os.path.join(self.__audio_path, "screenrecorder"))
            )
            self.__audio_capture_session.setRecorder(self.__audio_recorder)
        else:
            self.__video_recorder.setOutputLocation(QUrl.fromLocalFile(self.__filename))

    def start(self):
        try:
            self.__screen_to_record.start()
            self.__video_recorder.record()
            if self.__is_enabled_audio_recording:
                self.__audio_recorder.record()
            self.started.emit()
        except Exception as e:
            self.error.emit({
                "title": self.translations["SCREEN_RECORDER_ERROR_TITLE"],
                "message": self.translations["SCREEN_RECORDER_ERROR_MSG"],
                "details": str(e),
            })

    def stop(self):
        try:
            self.__video_recorder.stop()
            self.__screen_to_record.stop()
            if self.__is_enabled_audio_recording:
                self.__audio_recorder.stop()
        except Exception as e:
            self.error.emit({
                "title": self.translations["SCREEN_RECORDER_ERROR_TITLE"],
                "message": self.translations["SCREEN_RECORDER_ERROR_MSG"],
                "details": str(e),
            })

    def __join_audio_and_video(self):
        try:
            if self.__is_enabled_audio_recording:
                from moviepy import VideoFileClip, AudioFileClip

                output_path = self.__filename + ".mp4"
                audio_path = self.__get_file_path(self.__audio_path)
                video_path = self.__get_file_path(self.__video_path)
                video = VideoFileClip(video_path)
                audio = AudioFileClip(audio_path)
                video.set_audio(audio).write_videofile(output_path, codec="libx264", audio_codec="aac")

            self.finished.emit()
        except Exception as e:
            self.error.emit({
                "title": self.translations["SCREEN_RECORDER_ERROR_TITLE"],
                "message": self.translations["SCREEN_RECORDER_ERROR_MSG"],
                "details": str(e),
            })

    def __get_file_path(self, directory):
        for root, dirs, files in os.walk(directory):
            for file in files:
                if file.startswith("screenrecorder"):
                    return os.path.join(root, file)
        return None

    def __create_screen_recorder_directories(self):
        os.makedirs(self.__audio_path, exist_ok=True)
        os.makedirs(self.__video_path, exist_ok=True)


class TaskScreenRecorder(Task):
    def __init__(self, logger, progress_bar=None, status_bar=None):
        super().__init__(
            logger, 
            progress_bar,
            status_bar, 
            label="SCREEN_RECORDER",
            is_infinite_loop=True,
            worker_class=ScreenRecorderWorker
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

        super()._finished(status, details, self.translations["SCREEN_RECORDER_COMPLETED"].format(status.name))