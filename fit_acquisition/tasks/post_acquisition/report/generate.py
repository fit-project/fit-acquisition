#!/usr/bin/env python3
# -*- coding:utf-8 -*-
######
# -----
# Copyright (c) 2023 FIT-Project
# SPDX-License-Identifier: GPL-3.0-only
# -----
######

import base64
import fnmatch
import os

from jinja2 import Template
from importlib.resources import files

from xhtml2pdf import pisa
from PyPDF2 import PdfMerger
import zipfile

from fit_configurations.controller.tabs.general.typesproceedings import (
    TypesProceedings as TypesProceedingsController,
)

from fit_cases.model.case import Case
from fit_common.core.utils import get_version
from fit_configurations.utils import get_language

from fit_acquisition.lang import load_translations


class GenerateReport:
    def __init__(self, cases_folder_path, case_info):
        self.cases_folder_path = cases_folder_path
        self.output_front = os.path.join(self.cases_folder_path, "front_report.pdf")
        self.output_content = os.path.join(self.cases_folder_path, "content_report.pdf")
        self.output_front_result = open(self.output_front, "w+b")
        self.output_content_result = open(self.output_content, "w+b")
        case = Case()
        self.case_info = vars(case.get_from_id(case_info["id"]))

        language = get_language()

        if language == "Italian":
            self.translations = load_translations(lang="it")
        else:
            self.translations = load_translations()

    def generate_pdf(self, type, ntp):
        # PREPARING DATA TO FILL THE PDF
        if type == "web":
            try:
                with open(os.path.join(self.cases_folder_path, "whois.txt"), "r") as f:
                    whois_text = f.read()
                    f.close()
            except:
                whois_text = self.translations["NOT_PRODUCED"]
            if whois_text == "" or whois_text == "\n":
                whois_text = self.translations["NOT_PRODUCED"]

        hash_file_content = self.__hash_reader()
        screenshot = self.__insert_screenshot()
        video = self.__insert_video_hyperlink()

        proceeding_type = TypesProceedingsController().get_proceeding_name_by_id(
            self.case_info.get("proceeding_type", 0)
        )

        logo = self.case_info.get("logo_bin", "")
        if logo is not None:
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

        acquisition_files = self._acquisition_files_names()

        zip_enum = self._zip_files_enum()

        logo_path = files("fit_assets.images") / "logo-640x640.png"
        logo_bytes = logo_path.read_bytes()
        logo_base64 = base64.b64encode(logo_bytes).decode("utf-8")

        # FILLING FRONT PAGE WITH DATA
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

        # FILLING TEMPLATE WITH DATA
        if type == "web" and whois_text != self.translations["NOT_PRODUCED"]:

            template = Template(
                (files("fit_assets.templates") / "template_web.html").read_text(
                    encoding="utf-8"
                )
            )

            content_index = template.render(
                title=self.translations["TITLE"],
                index=self.translations["INDEX"],
                description=self.translations["DESCRIPTION"].format(
                    self.translations["RELEASES_LINK"]
                ),
                t1=self.translations["T1"],
                t2=self.translations["T2"],
                case=self.translations["CASEINFO"],
                casedata=self.translations["CASEDATA"],
                case0=self.translations["CASE"],
                case1=self.translations["LAWYER"],
                case2=self.translations["OPERATOR"],
                case3=self.translations["PROCEEDING"],
                case4=self.translations["COURT"],
                case5=self.translations["NUMBER"],
                case6=self.translations["ACQUISITION_TYPE"],
                case7=self.translations["ACQUISITION_DATE"],
                case8=self.translations["NOTES"],
                data0=str(self.case_info["name"] or "N/A"),
                data1=str(self.case_info["lawyer_name"] or "N/A"),
                data2=str(self.case_info["operator"] or "N/A"),
                data3=proceeding_type,
                data4=str(self.case_info["courthouse"] or "N/A"),
                data5=str(self.case_info["proceeding_number"] or "N/A"),
                data6=type,
                data7=ntp,
                data8=str(self.case_info["notes"] or "N/A").replace("\n", "<br>"),
                t3=self.translations["T3"],
                t3descr=self.translations["T3DESCR"],
                whoisfile=whois_text,
                t4=self.translations["T4"],
                t4descr=self.translations["T4DESCR"],
                name=self.translations["NAME"],
                descr=self.translations["DESCR"],
                avi=acquisition_files[
                    fnmatch.filter(acquisition_files.keys(), "*.avi")[0]
                ],
                avid=self.translations["AVID"],
                hash=acquisition_files["acquisition.hash"],
                hashd=self.translations["HASHD"],
                log=acquisition_files["acquisition.log"],
                logd=self.translations["LOGD"],
                pcap=acquisition_files["acquisition.pcap"],
                pcapd=self.translations["PCAPD"],
                zip=acquisition_files[
                    fnmatch.filter(acquisition_files.keys(), "*.zip")[0]
                ],
                zipd=self.translations["ZIPD"],
                whois=acquisition_files["whois.txt"],
                whoisd=self.translations["WHOISD"],
                headers=acquisition_files["headers.txt"],
                headersd=self.translations["HEADERSD"],
                nslookup=acquisition_files["nslookup.txt"],
                nslookupd=self.translations["NSLOOKUPD"],
                cer=acquisition_files["server.cer"],
                cerd=self.translations["CERD"],
                sslkey=acquisition_files["sslkey.log"],
                sslkeyd=self.translations["SSLKEYD"],
                traceroute=acquisition_files["traceroute.txt"],
                tracerouted=self.translations["TRACEROUTED"],
                t5=self.translations["T5"],
                t5descr=self.translations["T5DESCR"],
                file=hash_file_content,
                t6=self.translations["T6"],
                t6descr=self.translations["T6DESCR"],
                filedata=zip_enum,
                t7=self.translations["T7"],
                t7descr=self.translations["T7DESCR"],
                screenshot=screenshot,
                t8=self.translations["T8"],
                t8descr=self.translations["T8DESCR"],
                video_hyperlink=video,
                t9=self.translations["T9"],
                t9descr=self.translations["T9DESCR"],
                titlecc=self.translations["TITLECC"],
                ccdescr=self.translations["CCDESCR"],
                titleh=self.translations["TITLEH"],
                hdescr=self.translations["HDESCR"],
                page=self.translations["PAGE"],
                of=self.translations["OF"],
                logo=logo,
            )
            pdf_options = {
                "page-size": "Letter",
                "margin-top": "1in",
                "margin-right": "1in",
                "margin-bottom": "1in",
                "margin-left": "1in",
            }

            # create pdf front and content, merge them and remove merged files
            pisa.CreatePDF(
                front_index, dest=self.output_front_result, options=pdf_options
            )
            pisa.CreatePDF(
                content_index, dest=self.output_content_result, options=pdf_options
            )

        elif type == "web" and whois_text == self.translations["NOT_PRODUCED"]:

            template = Template(
                (
                    files("fit_assets.templates") / "template_web_no_whois.html"
                ).read_text(encoding="utf-8")
            )

            content_index = template.render(
                title=self.translations["TITLE"],
                index=self.translations["INDEX"],
                description=self.translations["DESCRIPTION"].format(
                    self.translations["RELEASES_LINK"]
                ),
                t1=self.translations["T1"],
                t2=self.translations["T2"],
                case=self.translations["CASEINFO"],
                casedata=self.translations["CASEDATA"],
                case0=self.translations["CASE"],
                case1=self.translations["LAWYER"],
                case2=self.translations["OPERATOR"],
                case3=self.translations["PROCEEDING"],
                case4=self.translations["COURT"],
                case5=self.translations["NUMBER"],
                case6=self.translations["ACQUISITION_TYPE"],
                case7=self.translations["ACQUISITION_DATE"],
                case8=self.translations["NOTES"],
                data0=str(self.case_info["name"] or "N/A"),
                data1=str(self.case_info["lawyer_name"] or "N/A"),
                data2=str(self.case_info["operator"] or "N/A"),
                data3=proceeding_type,
                data4=str(self.case_info["courthouse"] or "N/A"),
                data5=str(self.case_info["proceeding_number"] or "N/A"),
                data6=type,
                data7=ntp,
                data8=str(self.case_info["notes"] or "N/A").replace("\n", "<br>"),
                t4=self.translations["T4"],
                t4descr=self.translations["T4DESCR"],
                name=self.translations["NAME"],
                descr=self.translations["DESCR"],
                avi=acquisition_files[
                    fnmatch.filter(acquisition_files.keys(), "*.avi")[0]
                ],
                avid=self.translations["AVID"],
                hash=acquisition_files["acquisition.hash"],
                hashd=self.translations["HASHD"],
                log=acquisition_files["acquisition.log"],
                logd=self.translations["LOGD"],
                pcap=acquisition_files["acquisition.pcap"],
                pcapd=self.translations["PCAPD"],
                zip=acquisition_files[
                    fnmatch.filter(acquisition_files.keys(), "*.zip")[0]
                ],
                zipd=self.translations["ZIPD"],
                whois=acquisition_files["whois.txt"],
                whoisd=self.translations["WHOISD"],
                headers=acquisition_files["headers.txt"],
                headersd=self.translations["HEADERSD"],
                nslookup=acquisition_files["nslookup.txt"],
                nslookupd=self.translations["NSLOOKUPD"],
                cer=acquisition_files["server.cer"],
                cerd=self.translations["CERD"],
                sslkey=acquisition_files["sslkey.log"],
                sslkeyd=self.translations["SSLKEYD"],
                traceroute=acquisition_files["traceroute.txt"],
                tracerouted=self.translations["TRACEROUTED"],
                t5=self.translations["T5"],
                t5descr=self.translations["T5DESCR"],
                file=hash_file_content,
                t6=self.translations["T6"],
                t6descr=self.translations["T6DESCR"],
                filedata=zip_enum,
                t7=self.translations["T7"],
                t7descr=self.translations["T7DESCR"],
                screenshot=screenshot,
                t8=self.translations["T8"],
                t8descr=self.translations["T8DESCR"],
                video_hyperlink=video,
                t9=self.translations["T9"],
                t9descr=self.translations["T9DESCR"],
                titlecc=self.translations["TITLECC"],
                ccdescr=self.translations["CCDESCR"],
                titleh=self.translations["TITLEH"],
                hdescr=self.translations["HDESCR"],
                page=self.translations["PAGE"],
                of=self.translations["OF"],
                logo=logo,
            )

            pdf_options = {
                "page-size": "Letter",
                "margin-top": "1in",
                "margin-right": "1in",
                "margin-bottom": "1in",
                "margin-left": "1in",
            }
            # create pdf front and content, merge them and remove merged files
            pisa.CreatePDF(
                front_index, dest=self.output_front_result, options=pdf_options
            )
            pisa.CreatePDF(
                content_index, dest=self.output_content_result, options=pdf_options
            )

        if (
            type == "email"
            or type == "instagram"
            or type == "video"
            or type == "entire_website"
        ):

            template = Template(
                (files("fit_assets.templates") / "template_email.html").read_text(
                    encoding="utf-8"
                )
            )

            content_index = template.render(
                title=self.translations["TITLE"],
                index=self.translations["INDEX"],
                description=self.translations["DESCRIPTION"].format(
                    self.translations["RELEASES_LINK"]
                ),
                t1=self.translations["T1"],
                t2=self.translations["T2"],
                case=self.translations["CASEINFO"],
                casedata=self.translations["CASEDATA"],
                case0=self.translations["CASE"],
                case1=self.translations["LAWYER"],
                case2=self.translations["OPERATOR"],
                case3=self.translations["PROCEEDING"],
                case4=self.translations["COURT"],
                case5=self.translations["NUMBER"],
                case6=self.translations["ACQUISITION_TYPE"],
                case7=self.translations["ACQUISITION_DATE"],
                case8=self.translations["NOTES"],
                data0=str(self.case_info["name"] or "N/A"),
                data1=str(self.case_info["lawyer_name"] or "N/A"),
                data2=str(self.case_info["operator"] or "N/A"),
                data3=proceeding_type,
                data4=str(self.case_info["courthouse"] or "N/A"),
                data5=str(self.case_info["proceeding_number"] or "N/A"),
                data6=type,
                data7=ntp,
                data8=str(self.case_info["notes"] or "N/A").replace("\n", "<br>"),
                t4=self.translations["T4"],
                t4descr=self.translations["T4DESCR"],
                name=self.translations["NAME"],
                descr=self.translations["DESCR"],
                hash=acquisition_files["acquisition.hash"],
                hashd=self.translations["HASHD"],
                log=acquisition_files["acquisition.log"],
                logd=self.translations["LOGD"],
                zip=acquisition_files[
                    fnmatch.filter(acquisition_files.keys(), "*.zip")[0]
                ],
                zipd=self.translations["ZIPD"],
                t5=self.translations["T5"],
                t5descr=self.translations["T5DESCR"],
                file=hash_file_content,
                t6=self.translations["T6"],
                t6descr=self.translations["T6DESCR"],
                filedata=zip_enum,
                t7=self.translations["T7"],
                t7descr=self.translations["T7DESCR"],
                titlecc=self.translations["TITLECC"],
                ccdescr=self.translations["CCDESCR"],
                titleh=self.translations["TITLEH"],
                hdescr=self.translations["HDESCR"],
                page=self.translations["PAGE"],
                of=self.translations["OF"],
                logo=logo,
            )
            # create pdf front and content, merge them and remove merged files
            pisa.CreatePDF(front_index, dest=self.output_front_result)
            pisa.CreatePDF(content_index, dest=self.output_content_result)

        merger = PdfMerger()
        merger.append(self.output_front_result)
        merger.append(self.output_content_result)

        merger.write(os.path.join(self.cases_folder_path, "acquisition_report.pdf"))
        merger.close()
        self.output_content_result.close()
        self.output_front_result.close()
        if os.path.exists(self.output_front):
            os.remove(self.output_front)
        if os.path.exists(self.output_content):
            os.remove(self.output_content)

    def _acquisition_files_names(self):
        acquisition_files = {}
        files = [f.name for f in os.scandir(self.cases_folder_path) if f.is_file()]
        for file in files:
            acquisition_files[file] = file

        if not any(value.endswith(".avi") for value in acquisition_files.values()):
            acquisition_files["acquisition.avi"] = self.translations["NOT_PRODUCED"]
        if not "acquisition.hash" in acquisition_files.values():
            acquisition_files["acquisition.hash"] = self.translations["NOT_PRODUCED"]
        if not "acquisition.log" in acquisition_files.values():
            acquisition_files["acquisition.log"] = self.translations["NOT_PRODUCED"]
        if not any(value.endswith(".pcap") for value in acquisition_files.values()):
            acquisition_files["acquisition.pcap"] = self.translations["NOT_PRODUCED"]
        if not any(value.endswith(".zip") for value in acquisition_files.values()):
            acquisition_files["acquisition.zip"] = self.translations["NOT_PRODUCED"]
        if not "whois.txt" in acquisition_files.values():
            acquisition_files["whois.txt"] = self.translations["NOT_PRODUCED"]
        if not "headers.txt" in acquisition_files.values():
            acquisition_files["headers.txt"] = self.translations["NOT_PRODUCED"]
        if not "nslookup.txt" in acquisition_files.values():
            acquisition_files["nslookup.txt"] = self.translations["NOT_PRODUCED"]
        if not "server.cer" in acquisition_files.values():
            acquisition_files["server.cer"] = self.translations["NOT_PRODUCED"]
        if not "sslkey.log" in acquisition_files.values():
            acquisition_files["sslkey.log"] = self.translations["NOT_PRODUCED"]
        if not "traceroute.txt" in acquisition_files.values():
            acquisition_files["traceroute.txt"] = self.translations["NOT_PRODUCED"]

        return acquisition_files

    def _zip_files_enum(self):
        zip_enum = ""
        zip_dir = ""
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
        with open(
            os.path.join(
                self.cases_folder_path,
                "acquisition.hash",
            ),
            "r",
            encoding="latin-1",
        ) as f:
            for line in f:
                hash_text += "<p>" + line + "</p>"
        return hash_text

    def __insert_screenshot(self):
        screenshot_text = ""
        screenshots_path = os.path.join(self.cases_folder_path, "screenshot")

        if os.path.isdir(screenshots_path):
            full_screenshot_path = os.path.join(
                self.cases_folder_path, "screenshot", "full_page"
            )
            main_screenshot_file = os.path.join(
                self.cases_folder_path, "screenshot.png"
            )

            # url_folder = os.listdir(full_screenshot_path)
            url_folder = [
                file
                for file in os.listdir(full_screenshot_path)
                if os.path.isdir(os.path.join(full_screenshot_path, file))
            ]

            if url_folder:
                full_screenshot_path = os.path.join(full_screenshot_path, url_folder[0])

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
        if not any(value.endswith(".avi") for value in acquisition_files.values()):
            hyperlink = self.translations["NOT_PRODUCED"]
        else:
            hyperlink = (
                '<a href="file://'
                + self.cases_folder_path
                + '">'
                + self.translations["VIDEO_LINK"]
                + "</a>"
            )
        return hyperlink
