#!/usr/bin/env python3
# -*- coding:utf-8 -*-
######
# -----
# Copyright (c) 2023 FIT-Project
# SPDX-License-Identifier: LGPL-3.0-or-later
# -----
######

from PySide6 import QtCore, QtGui, QtWidgets

from fit_acquisition.lang import load_translations
from fit_common.core.utils import get_version


class Ui_acquisition_dialog_info(object):
    def setupUi(self, acquisition_dialog_info):
        acquisition_dialog_info.setObjectName("acquisition_dialog_info")
        acquisition_dialog_info.resize(500, 293)
        sizePolicy = QtWidgets.QSizePolicy(
            QtWidgets.QSizePolicy.Policy.Preferred,
            QtWidgets.QSizePolicy.Policy.Expanding,
        )
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(
            acquisition_dialog_info.sizePolicy().hasHeightForWidth()
        )
        acquisition_dialog_info.setSizePolicy(sizePolicy)
        acquisition_dialog_info.setMinimumSize(QtCore.QSize(0, 0))
        acquisition_dialog_info.setMaximumSize(QtCore.QSize(16777215, 16777215))
        acquisition_dialog_info.setStyleSheet(
            "QWidget{\n"
            "    color: rgb(221, 221, 221);\n"
            "    font:13px;\n"
            "}\n"
            "\n"
            "/* Content App */\n"
            "#content_top_bg{    \n"
            "    background-color: rgb(33, 37, 43);\n"
            "}\n"
            "\n"
            "/* Tooltip */\n"
            "QToolTip {\n"
            "    color: #e06133;\n"
            "    background-color: rgba(33, 37, 43, 180);\n"
            "    border: 1px solid rgb(44, 49, 58);\n"
            "    background-image: none;\n"
            "    background-position: left center;\n"
            "    background-repeat: no-repeat;\n"
            "    border: none;\n"
            "    border-left: 2px solid rgb(224, 97, 51);\n"
            "    text-align: left;\n"
            "    padding-left: 8px;\n"
            "    margin: 0px;\n"
            "}\n"
            "\n"
            "/* Top Buttons */\n"
            "#right_buttons .QPushButton { background-color: rgba(255, 255, 255, 0); border: none;  border-radius: 5px; }\n"
            "#right_buttons .QPushButton:hover { background-color: rgb(44, 49, 57); border-style: solid; border-radius: 4px; }\n"
            "#right_buttons .QPushButton:pressed { background-color: rgb(23, 26, 30); border-style: solid; border-radius: 4px; }\n"
            "\n"
            "/* Bottom Bar */\n"
            "#bottom_bar { background-color: rgb(44, 49, 58); }\n"
            "#bottom_bar QLabel { font-size: 11px; color: rgb(113, 126, 149); padding-left: 10px; padding-right: 10px; padding-bottom: 2px; }\n"
            ""
        )
        self.verticalLayoutWidget = QtWidgets.QWidget(parent=acquisition_dialog_info)
        self.verticalLayoutWidget.setGeometry(QtCore.QRect(0, 0, 502, 293))
        self.verticalLayoutWidget.setObjectName("verticalLayoutWidget")
        self.verticalLayout_2 = QtWidgets.QVBoxLayout(self.verticalLayoutWidget)
        self.verticalLayout_2.setSizeConstraint(
            QtWidgets.QLayout.SizeConstraint.SetDefaultConstraint
        )
        self.verticalLayout_2.setContentsMargins(0, 0, 0, 0)
        self.verticalLayout_2.setSpacing(0)
        self.verticalLayout_2.setObjectName("verticalLayout_2")
        self.content_top_bg = QtWidgets.QFrame(parent=self.verticalLayoutWidget)
        sizePolicy = QtWidgets.QSizePolicy(
            QtWidgets.QSizePolicy.Policy.Preferred,
            QtWidgets.QSizePolicy.Policy.Expanding,
        )
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(
            self.content_top_bg.sizePolicy().hasHeightForWidth()
        )
        self.content_top_bg.setSizePolicy(sizePolicy)
        self.content_top_bg.setMinimumSize(QtCore.QSize(500, 50))
        self.content_top_bg.setMaximumSize(QtCore.QSize(16777215, 50))
        self.content_top_bg.setFrameShape(QtWidgets.QFrame.Shape.NoFrame)
        self.content_top_bg.setFrameShadow(QtWidgets.QFrame.Shadow.Raised)
        self.content_top_bg.setObjectName("content_top_bg")
        self.horizontalLayout = QtWidgets.QHBoxLayout(self.content_top_bg)
        self.horizontalLayout.setContentsMargins(0, 0, 10, 0)
        self.horizontalLayout.setSpacing(0)
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.left_box = QtWidgets.QFrame(parent=self.content_top_bg)
        sizePolicy = QtWidgets.QSizePolicy(
            QtWidgets.QSizePolicy.Policy.Expanding,
            QtWidgets.QSizePolicy.Policy.Preferred,
        )
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.left_box.sizePolicy().hasHeightForWidth())
        self.left_box.setSizePolicy(sizePolicy)
        self.left_box.setFrameShape(QtWidgets.QFrame.Shape.NoFrame)
        self.left_box.setFrameShadow(QtWidgets.QFrame.Shadow.Raised)
        self.left_box.setObjectName("left_box")
        self.horizontalLayout_3 = QtWidgets.QHBoxLayout(self.left_box)
        self.horizontalLayout_3.setContentsMargins(0, 0, 0, 0)
        self.horizontalLayout_3.setSpacing(0)
        self.horizontalLayout_3.setObjectName("horizontalLayout_3")
        self.logo_container = QtWidgets.QFrame(parent=self.left_box)
        self.logo_container.setMinimumSize(QtCore.QSize(60, 0))
        self.logo_container.setMaximumSize(QtCore.QSize(60, 16777215))
        self.logo_container.setObjectName("logo_container")
        self.horizontalLayout_8 = QtWidgets.QHBoxLayout(self.logo_container)
        self.horizontalLayout_8.setContentsMargins(0, 0, 0, 0)
        self.horizontalLayout_8.setObjectName("horizontalLayout_8")
        self.top_logo = QtWidgets.QLabel(parent=self.logo_container)
        self.top_logo.setMinimumSize(QtCore.QSize(42, 42))
        self.top_logo.setMaximumSize(QtCore.QSize(42, 42))
        self.top_logo.setText("")
        self.top_logo.setPixmap(QtGui.QPixmap(":/images/images/logo-42x42.png"))
        self.top_logo.setObjectName("top_logo")
        self.horizontalLayout_8.addWidget(self.top_logo)
        self.horizontalLayout_3.addWidget(self.logo_container)
        self.title_right_info = QtWidgets.QLabel(parent=self.left_box)
        sizePolicy = QtWidgets.QSizePolicy(
            QtWidgets.QSizePolicy.Policy.Preferred,
            QtWidgets.QSizePolicy.Policy.Expanding,
        )
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(
            self.title_right_info.sizePolicy().hasHeightForWidth()
        )
        self.title_right_info.setSizePolicy(sizePolicy)
        self.title_right_info.setMaximumSize(QtCore.QSize(16777215, 45))
        self.title_right_info.setStyleSheet("font: 12pt;")
        self.title_right_info.setAlignment(
            QtCore.Qt.AlignmentFlag.AlignLeading
            | QtCore.Qt.AlignmentFlag.AlignLeft
            | QtCore.Qt.AlignmentFlag.AlignVCenter
        )
        self.title_right_info.setObjectName("title_right_info")
        self.horizontalLayout_3.addWidget(self.title_right_info)
        self.horizontalLayout.addWidget(self.left_box)
        self.right_buttons = QtWidgets.QFrame(parent=self.content_top_bg)
        self.right_buttons.setMinimumSize(QtCore.QSize(0, 28))
        self.right_buttons.setFrameShape(QtWidgets.QFrame.Shape.NoFrame)
        self.right_buttons.setFrameShadow(QtWidgets.QFrame.Shadow.Raised)
        self.right_buttons.setObjectName("right_buttons")
        self.horizontalLayout_2 = QtWidgets.QHBoxLayout(self.right_buttons)
        self.horizontalLayout_2.setContentsMargins(0, 0, 0, 0)
        self.horizontalLayout_2.setSpacing(5)
        self.horizontalLayout_2.setObjectName("horizontalLayout_2")
        self.minimize_button = QtWidgets.QPushButton(parent=self.right_buttons)
        self.minimize_button.setMinimumSize(QtCore.QSize(28, 28))
        self.minimize_button.setMaximumSize(QtCore.QSize(28, 28))
        self.minimize_button.setCursor(
            QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor)
        )
        self.minimize_button.setToolTip("")
        self.minimize_button.setText("")
        icon = QtGui.QIcon()
        icon.addPixmap(
            QtGui.QPixmap(":/icons/icons/icon_minimize-disabled.png"),
            QtGui.QIcon.Mode.Normal,
            QtGui.QIcon.State.Off,
        )
        self.minimize_button.setIcon(icon)
        self.minimize_button.setIconSize(QtCore.QSize(20, 20))
        self.minimize_button.setObjectName("minimize_button")
        self.horizontalLayout_2.addWidget(self.minimize_button)
        self.close_button = QtWidgets.QPushButton(parent=self.right_buttons)
        self.close_button.setMinimumSize(QtCore.QSize(28, 28))
        self.close_button.setMaximumSize(QtCore.QSize(28, 28))
        self.close_button.setCursor(
            QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor)
        )
        self.close_button.setToolTip("")
        self.close_button.setText("")
        icon1 = QtGui.QIcon()
        icon1.addPixmap(
            QtGui.QPixmap(":/icons/icons/icon_close-disabled.png"),
            QtGui.QIcon.Mode.Normal,
            QtGui.QIcon.State.Off,
        )
        self.close_button.setIcon(icon1)
        self.close_button.setIconSize(QtCore.QSize(20, 20))
        self.close_button.setObjectName("close_button")
        self.horizontalLayout_2.addWidget(self.close_button)
        self.horizontalLayout.addWidget(
            self.right_buttons, 0, QtCore.Qt.AlignmentFlag.AlignRight
        )
        self.verticalLayout_2.addWidget(self.content_top_bg)
        self.content_box = QtWidgets.QFrame(parent=self.verticalLayoutWidget)
        sizePolicy = QtWidgets.QSizePolicy(
            QtWidgets.QSizePolicy.Policy.Expanding,
            QtWidgets.QSizePolicy.Policy.Expanding,
        )
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.content_box.sizePolicy().hasHeightForWidth())
        self.content_box.setSizePolicy(sizePolicy)
        self.content_box.setMinimumSize(QtCore.QSize(0, 0))
        self.content_box.setMaximumSize(QtCore.QSize(16777215, 16777215))
        self.content_box.setStyleSheet("background-color: rgb(40, 44, 52);")
        self.content_box.setObjectName("content_box")
        self.content_box_layout = QtWidgets.QVBoxLayout(self.content_box)
        self.content_box_layout.setContentsMargins(12, 12, 12, 12)
        self.content_box_layout.setObjectName("content_box_layout")
        self.acquisition_table_info = QtWidgets.QTableWidget(parent=self.content_box)
        self.acquisition_table_info.setStyleSheet(
            "QHeaderView::section {\n"
            "    background-color: transparent;\n"
            "    color: white;\n"
            "}\n"
            ""
        )
        self.acquisition_table_info.setFrameShape(QtWidgets.QFrame.Shape.NoFrame)
        self.acquisition_table_info.setFrameShadow(QtWidgets.QFrame.Shadow.Plain)
        self.acquisition_table_info.setSizeAdjustPolicy(
            QtWidgets.QAbstractScrollArea.SizeAdjustPolicy.AdjustToContents
        )
        self.acquisition_table_info.setEditTriggers(
            QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers
        )
        self.acquisition_table_info.setTabKeyNavigation(False)
        self.acquisition_table_info.setProperty("showDropIndicator", False)
        self.acquisition_table_info.setSelectionMode(
            QtWidgets.QAbstractItemView.SelectionMode.NoSelection
        )
        self.acquisition_table_info.setTextElideMode(QtCore.Qt.TextElideMode.ElideRight)
        self.acquisition_table_info.setShowGrid(True)
        self.acquisition_table_info.setGridStyle(QtCore.Qt.PenStyle.SolidLine)
        self.acquisition_table_info.setWordWrap(True)
        self.acquisition_table_info.setCornerButtonEnabled(True)
        self.acquisition_table_info.setRowCount(0)
        self.acquisition_table_info.setColumnCount(0)
        self.acquisition_table_info.setObjectName("acquisition_table_info")
        self.acquisition_table_info.horizontalHeader().setVisible(True)
        self.acquisition_table_info.horizontalHeader().setCascadingSectionResizes(False)
        self.acquisition_table_info.horizontalHeader().setDefaultSectionSize(100)
        self.acquisition_table_info.horizontalHeader().setHighlightSections(False)
        self.acquisition_table_info.horizontalHeader().setSortIndicatorShown(False)
        self.acquisition_table_info.horizontalHeader().setStretchLastSection(True)
        self.acquisition_table_info.verticalHeader().setVisible(False)
        self.acquisition_table_info.verticalHeader().setCascadingSectionResizes(False)
        self.acquisition_table_info.verticalHeader().setHighlightSections(False)
        self.acquisition_table_info.verticalHeader().setStretchLastSection(False)
        self.content_box_layout.addWidget(self.acquisition_table_info)
        self.verticalLayout_2.addWidget(self.content_box)
        self.bottom_bar = QtWidgets.QFrame(parent=self.verticalLayoutWidget)
        self.bottom_bar.setMinimumSize(QtCore.QSize(0, 22))
        self.bottom_bar.setMaximumSize(QtCore.QSize(16777215, 22))
        self.bottom_bar.setFrameShape(QtWidgets.QFrame.Shape.NoFrame)
        self.bottom_bar.setFrameShadow(QtWidgets.QFrame.Shadow.Raised)
        self.bottom_bar.setObjectName("bottom_bar")
        self.horizontalLayout_6 = QtWidgets.QHBoxLayout(self.bottom_bar)
        self.horizontalLayout_6.setContentsMargins(0, 0, 0, 0)
        self.horizontalLayout_6.setSpacing(0)
        self.horizontalLayout_6.setObjectName("horizontalLayout_6")
        self.credits_label_2 = QtWidgets.QLabel(parent=self.bottom_bar)
        self.credits_label_2.setMaximumSize(QtCore.QSize(16777215, 16))
        self.credits_label_2.setAlignment(
            QtCore.Qt.AlignmentFlag.AlignLeading
            | QtCore.Qt.AlignmentFlag.AlignLeft
            | QtCore.Qt.AlignmentFlag.AlignVCenter
        )
        self.credits_label_2.setObjectName("credits_label_2")
        self.horizontalLayout_6.addWidget(self.credits_label_2)
        self.version = QtWidgets.QLabel(parent=self.bottom_bar)
        self.version.setAlignment(
            QtCore.Qt.AlignmentFlag.AlignRight
            | QtCore.Qt.AlignmentFlag.AlignTrailing
            | QtCore.Qt.AlignmentFlag.AlignVCenter
        )
        self.version.setObjectName("version")
        self.horizontalLayout_6.addWidget(self.version)
        self.frame_size_grip_2 = QtWidgets.QFrame(parent=self.bottom_bar)
        self.frame_size_grip_2.setMinimumSize(QtCore.QSize(20, 0))
        self.frame_size_grip_2.setMaximumSize(QtCore.QSize(20, 16777215))
        self.frame_size_grip_2.setFrameShape(QtWidgets.QFrame.Shape.NoFrame)
        self.frame_size_grip_2.setFrameShadow(QtWidgets.QFrame.Shadow.Raised)
        self.frame_size_grip_2.setObjectName("frame_size_grip_2")
        self.horizontalLayout_6.addWidget(self.frame_size_grip_2)
        self.verticalLayout_2.addWidget(self.bottom_bar)

        self.retranslateUi(acquisition_dialog_info)
        QtCore.QMetaObject.connectSlotsByName(acquisition_dialog_info)

    def retranslateUi(self, acquisition_dialog_info):
        _translate = QtCore.QCoreApplication.translate
        acquisition_dialog_info.setWindowTitle(
            _translate("acquisition_dialog_info", "FIT Tasks Info")
        )
        self.title_right_info.setText(
            _translate("acquisition_dialog_info", "Acquisition info")
        )
        self.acquisition_table_info.setSortingEnabled(False)
        self.credits_label_2.setText(
            _translate("acquisition_dialog_info", "By: fit-project.org")
        )
        self.version.setText(_translate("acquisition_dialog_info", "v1.0.3"))
