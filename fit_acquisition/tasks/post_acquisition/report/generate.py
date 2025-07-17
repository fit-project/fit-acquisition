#!/usr/bin/env python3
# -*- coding:utf-8 -*-
######
# -----
# Copyright (c) 2023 FIT-Project
# SPDX-License-Identifier: GPL-3.0-only
# -----
######

import base64
import os
import zipfile
from importlib.resources import files

from fit_common.core.utils import get_version
from fit_configurations.controller.tabs.general.legal_proceeding_type import (
    LegalProceedingTypeController,
)
from fit_configurations.controller.tabs.packet_capture.packet_capture import (
    PacketCaptureController,
)
from fit_configurations.controller.tabs.screen_recorder.screen_recorder import (
    ScreenRecorderController,
)
from fit_configurations.utils import get_language
from jinja2 import Template
from pypdf import PdfReader, PdfWriter
from xhtml2pdf import pisa

from fit_acquisition.lang import load_translations


class GenerateReport:
    def __init__(self, cases_folder_path, case_info):
        self.cases_folder_path = cases_folder_path
        self.output_front = os.path.join(self.cases_folder_path, "front_report.pdf")
        self.output_content = os.path.join(self.cases_folder_path, "content_report.pdf")
        self.case_info = case_info

        language = get_language()
        self.translations = (
            load_translations(lang="it")
            if language == "Italian"
            else load_translations()
        )

    def generate_pdf(self, type, ntp):

        logo_path = files("fit_assets.images") / "logo-640x640.png"
        logo_bytes = logo_path.read_bytes()
        logo_base64 = base64.b64encode(logo_bytes).decode("utf-8")

        # Front Page
        template = Template(
            (files("fit_assets.templates") / "front.html").read_text(encoding="utf-8")
        )

        front_index = template.render(
            img=f"data:image/png;base64,{logo_base64}",
            t1=self.translations["T1"],
            title=self.translations["TITLE"],
            report=self.translations["REPORT"],
            version=get_version(),
        )

        sections = []

        # FIT Description
        sections.append(
            {
                "title": self.translations["T1"],
                "type": "fit_description",
                "content": self.translations["DESCRIPTION"].format(
                    self.translations["RELEASES_LINK"]
                ),
            }
        )

        # Digital Forensics
        sections.append(
            {
                "title": self.translations["T4"],
                "type": "digital_forensics",
                "description": self.translations["T4DESCR"],
                "subtitles": {
                    "cc": self.translations["TITLECC"],
                    "h": self.translations["TITLEH"],
                },
                "contents": {
                    "cc": self.translations["CCDESCR"],
                    "h": self.translations["HDESCR"],
                },
            }
        )

        # Case Information
        case_rows = [
            {
                "value": self.translations["CASE"],
                "desc": self.case_info.get("name", "").strip() or "N/A",
            },
            {
                "value": self.translations["LAWYER"],
                "desc": self.case_info.get("lawyer_name", "").strip() or "N/A",
            },
            {
                "value": self.translations["OPERATOR"],
                "desc": self.case_info.get("operator", "").strip() or "N/A",
            },
            {
                "value": self.translations["PROCEEDING"],
                "desc": str(
                    LegalProceedingTypeController().get_proceeding_name_by_id(
                        self.case_info.get("proceeding_type", 0)
                    )
                ),
            },
            {
                "value": self.translations["COURT"],
                "desc": self.case_info.get("courthouse", "").strip() or "N/A",
            },
            {
                "value": self.translations["NUMBER"],
                "desc": self.case_info.get("proceeding_number", "").strip() or "N/A",
            },
            {"value": self.translations["ACQUISITION_TYPE"], "desc": type},
            {"value": self.translations["ACQUISITION_DATE"], "desc": ntp},
        ]

        sections.append(
            {
                "title": self.translations["T2"],
                "type": "case_info",
                "description": "",
                "columns": [
                    self.translations["CASEINFO"],
                    self.translations["CASEDATA"],
                ],
                "rows": case_rows,
                "note": self.case_info.get("notes", "").strip() or "N/A",
            }
        )

        # Company Logo
        logo = (self.case_info.get("logo_bin") or "").strip()
        if logo:
            logo = (
                '<div style="padding-bottom: 10px;"><img src="data:image/png;base64,'
                + base64.b64encode(logo).decode("utf-8")
                + '" height="'
                + self.case_info.get("logo_height", "")
                + '" width="'
                + self.case_info.get("logo_width", "")
                + '"></div>'
            )
        else:
            logo = "<div></div>"

        # Acquisition Files
        acquisition_files = self._acquisition_files_names()
        file_checks = [
            (
                ScreenRecorderController().configuration["filename"],
                self.translations["AVID"],
            ),
            ("acquisition.hash", self.translations["HASHD"]),
            ("acquisition.log", self.translations["LOGD"]),
            (
                PacketCaptureController().configuration["filename"],
                self.translations["PCAPD"],
            ),
            ("acquisition.zip", self.translations["ZIPD"]),
            ("whois.txt", self.translations["WHOISD"]),
            ("headers.txt", self.translations["HEADERSD"]),
            ("nslookup.txt", self.translations["NSLOOKUPD"]),
            ("server.cer", self.translations["CERD"]),
            ("sslkey.log", self.translations["SSLKEYD"]),
            ("traceroute.txt", self.translations["TRACEROUTED"]),
        ]

        file_rows = [
            {"value": acquisition_files[file], "desc": desc}
            for file, desc in file_checks
            if file in acquisition_files and acquisition_files[file]
        ]

        sections.append(
            {
                "title": self.translations["T5"],
                "type": "file_info",
                "description": self.translations["T5DESCR"],
                "columns": [self.translations["NAME"], self.translations["DESCR"]],
                "rows": file_rows,
                "note": "",
            }
        )

        # ZIP Content
        zip_enum = self._zip_files_enum()
        if zip_enum:
            sections.append(
                {
                    "title": self.translations["T7"],
                    "type": "zip_content",
                    "description": self.translations["T7DESCR"],
                    "content": zip_enum,
                }
            )

        # hash
        hash_content = self.__hash_reader()
        if hash_content:
            sections.append(
                {
                    "title": self.translations["T6"],
                    "type": "hash",
                    "description": self.translations["T6DESCR"],
                    "content": hash_content,
                }
            )

        # whois
        whois_content = self.__read_file("whois.txt")
        if whois_content:
            sections.append(
                {
                    "title": self.translations["T3"],
                    "type": "whois",
                    "description": self.translations["T3DESCR"],
                    "content": whois_content,
                }
            )

        # Screenshots
        screenshot_content = self.__insert_screenshot()
        if screenshot_content:
            sections.append(
                {
                    "title": self.translations["T8"],
                    "type": "screenshot",
                    "description": self.translations["T8DESCR"],
                    "content": screenshot_content,
                }
            )

        # Video
        video_content = self.__insert_video_hyperlink()
        if video_content:
            sections.append(
                {
                    "title": self.translations["T9"],
                    "type": "video",
                    "description": self.translations["T9DESCR"],
                    "content": video_content,
                }
            )

        template = Template(
            (files("fit_assets.templates") / "content.html").read_text(encoding="utf-8")
        )

        content_index = template.render(
            title=self.translations["TITLE"],
            t1=self.translations["T1"],
            index=self.translations["INDEX"],
            sections=sections,
            note=self.translations["NOTE"],
            logo=logo,
            page=self.translations["PAGE"],
            of=self.translations["OF"],
        )

        pdf_options = {
            "page-size": "Letter",
            "margin-top": "1in",
            "margin-right": "1in",
            "margin-bottom": "1in",
            "margin-left": "1in",
        }

        # create pdf front and content, merge them and remove merged files
        with open(self.output_front, "w+b") as front_result:
            pisa.CreatePDF(front_index, dest=front_result, options=pdf_options)

        with open(self.output_content, "w+b") as content_result:
            pisa.CreatePDF(content_index, dest=content_result, options=pdf_options)

        writer = PdfWriter()
        with open(self.output_front, "rb") as f_front:
            reader_front = PdfReader(f_front)
            for page in reader_front.pages:
                writer.add_page(page)

        with open(self.output_content, "rb") as f_content:
            reader_content = PdfReader(f_content)
            for page in reader_content.pages:
                writer.add_page(page)

        output_path = os.path.join(self.cases_folder_path, "acquisition_report.pdf")
        with open(output_path, "wb") as f_out:
            writer.write(f_out)

        if os.path.exists(self.output_front):
            os.remove(self.output_front)
        if os.path.exists(self.output_content):
            os.remove(self.output_content)

    def __read_file(self, filename):
        try:
            file_path = os.path.join(self.cases_folder_path, filename)
            if os.path.getsize(file_path) == 0:
                return None
            with open(file_path, "r") as f:
                content = f.read()
                return content if content.strip() else None
        except (FileNotFoundError, OSError):
            return None
        except FileNotFoundError:
            return None
        except FileNotFoundError:
            return None

    def _acquisition_files_names(self):
        acquisition_files = {}
        files = [f.name for f in os.scandir(self.cases_folder_path) if f.is_file()]
        for file in files:
            acquisition_files[file] = file

        screen_recorder_filename = ScreenRecorderController().configuration["filename"]
        packet_capture_filename = PacketCaptureController().configuration["filename"]

        file_checks = [
            screen_recorder_filename,
            "acquisition.hash",
            "acquisition.log",
            packet_capture_filename,
            "acquisition.zip",
            "whois.txt",
            "headers.txt",
            "nslookup.txt",
            "server.cer",
            "sslkey.log",
            "traceroute.txt",
        ]

        for filename in file_checks:
            matching_files = [
                file for file in acquisition_files.values() if file.startswith(filename)
            ]

            if not matching_files:
                acquisition_files.pop(filename, None)
            else:
                actual_file = matching_files[0]
                if self.__is_empty_file(actual_file):
                    acquisition_files[actual_file] = self.translations[
                        "EMPTY_FILE"
                    ].format(actual_file)

        return acquisition_files

    def __is_empty_file(self, filename):
        path = os.path.join(self.cases_folder_path, filename)
        return not os.path.isfile(path) or os.path.getsize(path) == 0

    def _zip_files_enum(self):
        zip_enum = None
        zip_dir = None
        # getting zip folder and passing file names and dimensions to the template
        for fname in os.listdir(self.cases_folder_path):
            if fname.endswith(".zip"):
                zip_dir = os.path.join(self.cases_folder_path, fname)

        if zip_dir:
            zip_folder = zipfile.ZipFile(zip_dir)
            for zip_file in zip_folder.filelist:
                size = zip_file.file_size
                filename = zip_file.filename
                if filename.count(".") > 1:
                    filename = filename.rsplit(".", 1)[0]
                else:
                    pass
                if size > 0:
                    zip_enum += "<p>" + filename + "</p>"
                    zip_enum += (
                        "<p>" + self.translations["SIZE"] + str(size) + " bytes</p>"
                    )
                    zip_enum += "<hr>"
        return zip_enum

    def __hash_reader(self):
        hash_text = ""
        filename = "acquisition.hash"

        if self.__read_file(filename):
            with open(
                os.path.join(
                    self.cases_folder_path,
                    filename,
                ),
                "r",
                encoding="latin-1",
            ) as f:
                for line in f:
                    hash_text += "<p>" + line + "</p>"

        return hash_text

    def __insert_screenshot(self):
        screenshot_text = ""
        main_screenshot = ""
        screenshots_path = os.path.join(self.cases_folder_path, "screenshot")
        full_screenshot_path = os.path.join(
            self.cases_folder_path, "screenshot", "full_page"
        )

        if os.path.isdir(screenshots_path):
            main_screenshot_file = os.path.join(
                self.cases_folder_path, "screenshot.png"
            )

            if os.path.isdir(full_screenshot_path):
                url_folder = [
                    file
                    for file in os.listdir(full_screenshot_path)
                    if os.path.isdir(os.path.join(full_screenshot_path, file))
                ]

                if url_folder:
                    full_screenshot_path = os.path.join(
                        full_screenshot_path, url_folder[0]
                    )

                images = os.listdir(full_screenshot_path)
                main_screenshot = os.path.join(full_screenshot_path, images[0])

            files = os.listdir(screenshots_path)
            for file in files:
                path = os.path.join(self.cases_folder_path, "screenshot", file)
                if os.path.isfile(path):
                    if "full_page_" not in os.path.basename(file):
                        screenshot_text += (
                            "<p>"
                            '<a href="file://'
                            + path
                            + '">'
                            + "Screenshot"
                            + os.path.basename(file)
                            + '</a><br><img src="'
                            + path
                            + '"></p><br><br>'
                        )

            # main full page screenshot
            screenshot_text += (
                "<p>"
                '<a href="file://'
                + main_screenshot_file
                + '">'
                + self.translations["COMPLETE_SCREENSHOT"]
                + '</a><br><img src="'
                + main_screenshot
                + '"></p>'
            )

        return screenshot_text

    def __insert_video_hyperlink(self):
        acquisition_files = {}
        files = [f.name for f in os.scandir(self.cases_folder_path) if f.is_file()]
        for file in files:
            acquisition_files[file] = file

        screen_recorder_filename = ScreenRecorderController().configuration["filename"]

        matching_files = [
            file
            for file in acquisition_files.values()
            if file.startswith(screen_recorder_filename)
        ]

        if matching_files:
            actual_filename = matching_files[0]
            hyperlink = (
                '<a href="file://'
                + os.path.join(self.cases_folder_path, actual_filename)
                + '">'
                + self.translations["VIDEO_LINK"]
                + "</a>"
            )
        else:
            hyperlink = None

        return hyperlink
