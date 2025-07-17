# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'tasks_info.ui'
##
## Created by: Qt User Interface Compiler version 6.8.2
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import (QCoreApplication, QDate, QDateTime, QLocale,
    QMetaObject, QObject, QPoint, QRect,
    QSize, QTime, QUrl, Qt)
from PySide6.QtGui import (QBrush, QColor, QConicalGradient, QCursor,
    QFont, QFontDatabase, QGradient, QIcon,
    QImage, QKeySequence, QLinearGradient, QPainter,
    QPalette, QPixmap, QRadialGradient, QTransform)
from PySide6.QtWidgets import (QApplication, QFrame, QLayout, QSizePolicy,
    QTextEdit, QVBoxLayout, QWidget)

class Ui_tasks_info(object):
    def setupUi(self, tasks_info):
        if not tasks_info.objectName():
            tasks_info.setObjectName(u"tasks_info")
        tasks_info.resize(800, 600)
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(tasks_info.sizePolicy().hasHeightForWidth())
        tasks_info.setSizePolicy(sizePolicy)
        tasks_info.setMinimumSize(QSize(0, 0))
        tasks_info.setMaximumSize(QSize(16777215, 16777215))
        tasks_info.setStyleSheet(u"QWidget{\n"
"	color: rgb(221, 221, 221);\n"
"	font:13px;\n"
"}\n"
"\n"
"")
        self.verticalLayout_2 = QVBoxLayout(tasks_info)
        self.verticalLayout_2.setSpacing(0)
        self.verticalLayout_2.setObjectName(u"verticalLayout_2")
        self.verticalLayout_2.setSizeConstraint(QLayout.SetDefaultConstraint)
        self.verticalLayout_2.setContentsMargins(0, 0, 0, 0)
        self.content_box = QFrame(tasks_info)
        self.content_box.setObjectName(u"content_box")
        self.content_box.setEnabled(True)
        sizePolicy1 = QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        sizePolicy1.setHorizontalStretch(0)
        sizePolicy1.setVerticalStretch(0)
        sizePolicy1.setHeightForWidth(self.content_box.sizePolicy().hasHeightForWidth())
        self.content_box.setSizePolicy(sizePolicy1)
        self.content_box.setMinimumSize(QSize(0, 0))
        self.content_box.setMaximumSize(QSize(16777215, 16777215))
        self.content_box.setStyleSheet(u"background-color: rgb(40, 44, 52);")
        self.content_box_layout = QVBoxLayout(self.content_box)
        self.content_box_layout.setObjectName(u"content_box_layout")
        self.content_box_layout.setContentsMargins(12, 12, 12, 12)
        self.task_log_text = QTextEdit(self.content_box)
        self.task_log_text.setObjectName(u"task_log_text")
        self.task_log_text.setStyleSheet(u"\n"
"              color: white;\n"
"            ")
        font = QFont()
        font.setBold(False)
        font.setItalic(False)
        self.task_log_text.setFont(font)
        self.task_log_text.setReadOnly(True)

        self.content_box_layout.addWidget(self.task_log_text)


        self.verticalLayout_2.addWidget(self.content_box)


        self.retranslateUi(tasks_info)

        QMetaObject.connectSlotsByName(tasks_info)
    # setupUi

    def retranslateUi(self, tasks_info):
        tasks_info.setWindowTitle(QCoreApplication.translate("tasks_info", u"Tasks Info", None))
    # retranslateUi

