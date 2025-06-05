# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'light_tool.ui'
##
## Created by: Qt User Interface Compiler version 6.9.0
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
from PySide6.QtWidgets import (QApplication, QFrame, QGridLayout, QLabel,
    QPushButton, QSizePolicy, QSplitter, QVBoxLayout,
    QWidget)

class Ui_light_tool(object):
    def setupUi(self, light_tool):
        if not light_tool.objectName():
            light_tool.setObjectName(u"light_tool")
        light_tool.resize(280, 174)
        light_tool.setMaximumSize(QSize(280, 16777215))
        self.verticalLayout = QVBoxLayout(light_tool)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.frame = QFrame(light_tool)
        self.frame.setObjectName(u"frame")
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.frame.sizePolicy().hasHeightForWidth())
        self.frame.setSizePolicy(sizePolicy)
        self.frame.setMaximumSize(QSize(280, 16777215))
        self.frame.setFrameShape(QFrame.Shape.StyledPanel)
        self.frame.setFrameShadow(QFrame.Shadow.Raised)
        self.gridLayout = QGridLayout(self.frame)
        self.gridLayout.setObjectName(u"gridLayout")
        self.splitter_3 = QSplitter(self.frame)
        self.splitter_3.setObjectName(u"splitter_3")
        self.splitter_3.setOrientation(Qt.Orientation.Vertical)
        self.splitter_3.setHandleWidth(0)
        self.splitter = QSplitter(self.splitter_3)
        self.splitter.setObjectName(u"splitter")
        self.splitter.setOrientation(Qt.Orientation.Horizontal)
        self.splitter.setHandleWidth(0)
        self.label_168 = QLabel(self.splitter)
        self.label_168.setObjectName(u"label_168")
        sizePolicy1 = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        sizePolicy1.setHorizontalStretch(0)
        sizePolicy1.setVerticalStretch(0)
        sizePolicy1.setHeightForWidth(self.label_168.sizePolicy().hasHeightForWidth())
        self.label_168.setSizePolicy(sizePolicy1)
        self.label_168.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.splitter.addWidget(self.label_168)
        self.pushButton_293 = QPushButton(self.splitter)
        self.pushButton_293.setObjectName(u"pushButton_293")
        sizePolicy2 = QSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        sizePolicy2.setHorizontalStretch(0)
        sizePolicy2.setVerticalStretch(0)
        sizePolicy2.setHeightForWidth(self.pushButton_293.sizePolicy().hasHeightForWidth())
        self.pushButton_293.setSizePolicy(sizePolicy2)
        self.pushButton_293.setMaximumSize(QSize(30, 30))
        self.splitter.addWidget(self.pushButton_293)
        self.splitter_3.addWidget(self.splitter)
        self.splitter_2 = QSplitter(self.splitter_3)
        self.splitter_2.setObjectName(u"splitter_2")
        self.splitter_2.setOrientation(Qt.Orientation.Horizontal)
        self.splitter_2.setHandleWidth(0)
        self.main_Firefly = QPushButton(self.splitter_2)
        self.main_Firefly.setObjectName(u"main_Firefly")
        self.splitter_2.addWidget(self.main_Firefly)
        self.main_Object_Light = QPushButton(self.splitter_2)
        self.main_Object_Light.setObjectName(u"main_Object_Light")
        self.splitter_2.addWidget(self.main_Object_Light)
        self.main_lightning = QPushButton(self.splitter_2)
        self.main_lightning.setObjectName(u"main_lightning")
        self.splitter_2.addWidget(self.main_lightning)
        self.splitter_3.addWidget(self.splitter_2)
        self.label_172 = QLabel(self.splitter_3)
        self.label_172.setObjectName(u"label_172")
        self.label_172.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.splitter_3.addWidget(self.label_172)
        self.splitter_390 = QSplitter(self.splitter_3)
        self.splitter_390.setObjectName(u"splitter_390")
        self.splitter_390.setOrientation(Qt.Orientation.Horizontal)
        self.splitter_390.setHandleWidth(0)
        self.sub_pulse = QPushButton(self.splitter_390)
        self.sub_pulse.setObjectName(u"sub_pulse")
        self.splitter_390.addWidget(self.sub_pulse)
        self.sub_flicker = QPushButton(self.splitter_390)
        self.sub_flicker.setObjectName(u"sub_flicker")
        self.splitter_390.addWidget(self.sub_flicker)
        self.sub_glow_spread = QPushButton(self.splitter_390)
        self.sub_glow_spread.setObjectName(u"sub_glow_spread")
        self.splitter_390.addWidget(self.sub_glow_spread)
        self.splitter_3.addWidget(self.splitter_390)
        self.splitter_391 = QSplitter(self.splitter_3)
        self.splitter_391.setObjectName(u"splitter_391")
        self.splitter_391.setOrientation(Qt.Orientation.Horizontal)
        self.splitter_391.setHandleWidth(0)
        self.sub_trail = QPushButton(self.splitter_391)
        self.sub_trail.setObjectName(u"sub_trail")
        self.splitter_391.addWidget(self.sub_trail)
        self.sub_spark = QPushButton(self.splitter_391)
        self.sub_spark.setObjectName(u"sub_spark")
        self.splitter_391.addWidget(self.sub_spark)
        self.sub_flash = QPushButton(self.splitter_391)
        self.sub_flash.setObjectName(u"sub_flash")
        self.splitter_391.addWidget(self.sub_flash)
        self.splitter_3.addWidget(self.splitter_391)
        self.splitter_393 = QSplitter(self.splitter_3)
        self.splitter_393.setObjectName(u"splitter_393")
        self.splitter_393.setOrientation(Qt.Orientation.Horizontal)
        self.splitter_393.setHandleWidth(0)
        self.sub_radius_glow = QPushButton(self.splitter_393)
        self.sub_radius_glow.setObjectName(u"sub_radius_glow")
        self.splitter_393.addWidget(self.sub_radius_glow)
        self.sub_focus_pulse = QPushButton(self.splitter_393)
        self.sub_focus_pulse.setObjectName(u"sub_focus_pulse")
        self.splitter_393.addWidget(self.sub_focus_pulse)
        self.pushButton_3 = QPushButton(self.splitter_393)
        self.pushButton_3.setObjectName(u"pushButton_3")
        self.splitter_393.addWidget(self.pushButton_3)
        self.splitter_3.addWidget(self.splitter_393)
        self.splitter_395 = QSplitter(self.splitter_3)
        self.splitter_395.setObjectName(u"splitter_395")
        self.splitter_395.setOrientation(Qt.Orientation.Vertical)
        self.splitter_395.setHandleWidth(0)
        self.splitter_3.addWidget(self.splitter_395)

        self.gridLayout.addWidget(self.splitter_3, 1, 0, 1, 1)


        self.verticalLayout.addWidget(self.frame)


        self.retranslateUi(light_tool)

        QMetaObject.connectSlotsByName(light_tool)
    # setupUi

    def retranslateUi(self, light_tool):
        light_tool.setWindowTitle(QCoreApplication.translate("light_tool", u"Form", None))
        self.label_168.setText(QCoreApplication.translate("light_tool", u"light", None))
        self.pushButton_293.setText(QCoreApplication.translate("light_tool", u"X", None))
        self.main_Firefly.setText(QCoreApplication.translate("light_tool", u"Firefly", None))
        self.main_Object_Light.setText(QCoreApplication.translate("light_tool", u"Object Light", None))
        self.main_lightning.setText(QCoreApplication.translate("light_tool", u"lightning", None))
        self.label_172.setText(QCoreApplication.translate("light_tool", u"sub functions", None))
        self.sub_pulse.setText(QCoreApplication.translate("light_tool", u"pulse", None))
        self.sub_flicker.setText(QCoreApplication.translate("light_tool", u"flicker", None))
        self.sub_glow_spread.setText(QCoreApplication.translate("light_tool", u"glow spread", None))
        self.sub_trail.setText(QCoreApplication.translate("light_tool", u"trail", None))
        self.sub_spark.setText(QCoreApplication.translate("light_tool", u"spark", None))
        self.sub_flash.setText(QCoreApplication.translate("light_tool", u"flash", None))
        self.sub_radius_glow.setText(QCoreApplication.translate("light_tool", u"radius glow", None))
        self.sub_focus_pulse.setText(QCoreApplication.translate("light_tool", u"focus pulse", None))
        self.pushButton_3.setText(QCoreApplication.translate("light_tool", u"branches", None))
    # retranslateUi

