#!/usr/bin/env python3
# -*- coding:utf-8 -*-
######
# -----
# Copyright (c) 2023 FIT-Project
# SPDX-License-Identifier: GPL-3.0-only
# -----
######

from enum import Enum


class LoggerName(str, Enum):
    SCRAPER_WEB = 'scraper.web'
    SCRAPER_MAIL = 'scraper.mail'
    SCRAPER_INSTAGRAM = 'scraper.instagram'
    SCRAPER_VIDEO = 'scraper.video'
    SCRAPER_ENTIRE_WEBSITE = 'scraper.entire_website'
    HASHREPORT = 'hashreport'
