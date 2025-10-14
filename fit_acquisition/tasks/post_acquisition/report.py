#!/usr/bin/env python3
# -*- coding:utf-8 -*-
######
# -----
# Copyright (c) 2023 FIT-Project
# SPDX-License-Identifier: GPL-3.0-only
# -----
######


from fit_common.core import debug, get_context, get_ntp_date_and_time, log_exception
from fit_common.core.pdf_report_builder import PdfReportBuilder, ReportType
from fit_common.gui.utils import Status
from fit_configurations.controller.tabs.general.legal_proceeding_type import (
    LegalProceedingTypeController,
)
from fit_configurations.controller.tabs.network.network_check import (
    NetworkCheckController,
)
from fit_configurations.controller.tabs.packet_capture.packet_capture import (
    PacketCaptureController,
)
from fit_configurations.controller.tabs.screen_recorder.screen_recorder import (
    ScreenRecorderController,
)
from fit_configurations.utils import get_language

from fit_acquisition.lang import load_translations
from fit_acquisition.tasks.task import Task
from fit_acquisition.tasks.task_worker import TaskWorker


class ReportWorker(TaskWorker):

    def start(self):
        self.started.emit()
        language = get_language()
        translations = (
            load_translations(lang="it")
            if language == "Italian"
            else load_translations()
        )
        screen_recorder_filename = ScreenRecorderController().configuration["filename"]
        packet_capture_filename = PacketCaptureController().configuration["filename"]
        case_info = self.options["case_info"]
        case_info[
            "proceeding_type_name"
        ] = LegalProceedingTypeController().get_proceeding_name_by_id(
            case_info.get("proceeding_type", 0)
        )

        try:
            report = PdfReportBuilder(
                ReportType.ACQUISITION,
                translations=translations,
                path=self.options["acquisition_directory"],
                filename="acquisition_report.pdf",
                case_info=case_info,
                screen_recorder_filename=screen_recorder_filename,
                packet_capture_filename=packet_capture_filename,
            )
            report.acquisition_type = self.options["type"]
            report.ntp = get_ntp_date_and_time(
                NetworkCheckController().configuration["ntp_server"]
            )
            report.generate_pdf()
            self.finished.emit()
        except Exception as e:
            log_exception(e, context=get_context(self))
            debug(
                "Start report failed",
                str(e),
                context=get_context(self),
            )
            self.error.emit(
                {
                    "title": self.translations["REPORTFILE"],
                    "message": self.translations["GENERATE_PDF_REPORT_FAILED_MGS"],
                    "details": str(e),
                }
            )


class TaskReport(Task):
    def __init__(self, logger, progress_bar=None, status_bar=None):
        super().__init__(
            logger,
            progress_bar,
            status_bar,
            label="REPORTFILE",
            worker_class=ReportWorker,
        )

    def start(self):
        super().start_task(self.translations["GENERATE_PDF_REPORT_STARTED"])

    def _finished(self, status=Status.SUCCESS, details=""):
        message = self.translations["GENERATE_PDF_REPORT_COMPLETED"].format(status.name)
        super()._finished(status, details, message)
