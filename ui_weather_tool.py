# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'weather_tool.ui'
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
    QPushButton, QSizePolicy, QSplitter, QWidget)

class Ui_weather_tool(object):
    def setupUi(self, weather_tool):
        if not weather_tool.objectName():
            weather_tool.setObjectName(u"weather_tool")
        weather_tool.resize(280, 198)
        weather_tool.setMaximumSize(QSize(280, 16777215))
        self.gridLayout = QGridLayout(weather_tool)
        self.gridLayout.setObjectName(u"gridLayout")
        self.frame = QFrame(weather_tool)
        self.frame.setObjectName(u"frame")
        self.frame.setMaximumSize(QSize(280, 16777215))
        self.frame.setFrameShape(QFrame.Shape.StyledPanel)
        self.frame.setFrameShadow(QFrame.Shadow.Raised)
        self.gridLayout_2 = QGridLayout(self.frame)
        self.gridLayout_2.setObjectName(u"gridLayout_2")
        self.splitter_328 = QSplitter(self.frame)
        self.splitter_328.setObjectName(u"splitter_328")
        self.splitter_328.setOrientation(Qt.Orientation.Vertical)
        self.splitter_328.setHandleWidth(0)
        self.splitter_329 = QSplitter(self.splitter_328)
        self.splitter_329.setObjectName(u"splitter_329")
        self.splitter_329.setOrientation(Qt.Orientation.Horizontal)
        self.splitter_329.setHandleWidth(0)
        self.sub_fade_fluctuations = QPushButton(self.splitter_329)
        self.sub_fade_fluctuations.setObjectName(u"sub_fade_fluctuations")
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.sub_fade_fluctuations.sizePolicy().hasHeightForWidth())
        self.sub_fade_fluctuations.setSizePolicy(sizePolicy)
        self.splitter_329.addWidget(self.sub_fade_fluctuations)
        self.sub_heat_lift = QPushButton(self.splitter_329)
        self.sub_heat_lift.setObjectName(u"sub_heat_lift")
        self.splitter_329.addWidget(self.sub_heat_lift)
        self.splitter_328.addWidget(self.splitter_329)
        self.splitter_330 = QSplitter(self.splitter_328)
        self.splitter_330.setObjectName(u"splitter_330")
        self.splitter_330.setOrientation(Qt.Orientation.Horizontal)
        self.splitter_330.setHandleWidth(0)
        self.splitter_328.addWidget(self.splitter_330)

        self.gridLayout_2.addWidget(self.splitter_328, 5, 0, 1, 1)

        self.splitter_301 = QSplitter(self.frame)
        self.splitter_301.setObjectName(u"splitter_301")
        self.splitter_301.setMaximumSize(QSize(16777215, 24))
        self.splitter_301.setOrientation(Qt.Orientation.Horizontal)
        self.splitter_301.setHandleWidth(0)
        self.label_161 = QLabel(self.splitter_301)
        self.label_161.setObjectName(u"label_161")
        sizePolicy1 = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        sizePolicy1.setHorizontalStretch(0)
        sizePolicy1.setVerticalStretch(0)
        sizePolicy1.setHeightForWidth(self.label_161.sizePolicy().hasHeightForWidth())
        self.label_161.setSizePolicy(sizePolicy1)
        self.label_161.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.splitter_301.addWidget(self.label_161)
        self.pushButton_252 = QPushButton(self.splitter_301)
        self.pushButton_252.setObjectName(u"pushButton_252")
        sizePolicy2 = QSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        sizePolicy2.setHorizontalStretch(0)
        sizePolicy2.setVerticalStretch(0)
        sizePolicy2.setHeightForWidth(self.pushButton_252.sizePolicy().hasHeightForWidth())
        self.pushButton_252.setSizePolicy(sizePolicy2)
        self.pushButton_252.setMaximumSize(QSize(30, 30))
        self.splitter_301.addWidget(self.pushButton_252)

        self.gridLayout_2.addWidget(self.splitter_301, 1, 0, 1, 1)

        self.label_162 = QLabel(self.frame)
        self.label_162.setObjectName(u"label_162")
        self.label_162.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.gridLayout_2.addWidget(self.label_162, 3, 0, 1, 1)

        self.splitter_325 = QSplitter(self.frame)
        self.splitter_325.setObjectName(u"splitter_325")
        self.splitter_325.setOrientation(Qt.Orientation.Vertical)
        self.splitter_325.setHandleWidth(0)
        self.splitter_326 = QSplitter(self.splitter_325)
        self.splitter_326.setObjectName(u"splitter_326")
        self.splitter_326.setOrientation(Qt.Orientation.Horizontal)
        self.splitter_326.setHandleWidth(0)
        self.sub_swirls = QPushButton(self.splitter_326)
        self.sub_swirls.setObjectName(u"sub_swirls")
        self.splitter_326.addWidget(self.sub_swirls)
        self.sub_drift = QPushButton(self.splitter_326)
        self.sub_drift.setObjectName(u"sub_drift")
        sizePolicy.setHeightForWidth(self.sub_drift.sizePolicy().hasHeightForWidth())
        self.sub_drift.setSizePolicy(sizePolicy)
        self.splitter_326.addWidget(self.sub_drift)
        self.splitter_325.addWidget(self.splitter_326)
        self.splitter_327 = QSplitter(self.splitter_325)
        self.splitter_327.setObjectName(u"splitter_327")
        self.splitter_327.setOrientation(Qt.Orientation.Horizontal)
        self.splitter_327.setHandleWidth(0)
        self.sub_gusts = QPushButton(self.splitter_327)
        self.sub_gusts.setObjectName(u"sub_gusts")
        self.splitter_327.addWidget(self.sub_gusts)
        self.sub_density_pulse = QPushButton(self.splitter_327)
        self.sub_density_pulse.setObjectName(u"sub_density_pulse")
        self.splitter_327.addWidget(self.sub_density_pulse)
        self.splitter_325.addWidget(self.splitter_327)

        self.gridLayout_2.addWidget(self.splitter_325, 4, 0, 1, 1)

        self.splitter_322 = QSplitter(self.frame)
        self.splitter_322.setObjectName(u"splitter_322")
        sizePolicy2.setHeightForWidth(self.splitter_322.sizePolicy().hasHeightForWidth())
        self.splitter_322.setSizePolicy(sizePolicy2)
        self.splitter_322.setOrientation(Qt.Orientation.Vertical)
        self.splitter_322.setHandleWidth(0)
        self.splitter_323 = QSplitter(self.splitter_322)
        self.splitter_323.setObjectName(u"splitter_323")
        self.splitter_323.setMaximumSize(QSize(16777215, 24))
        self.splitter_323.setOrientation(Qt.Orientation.Horizontal)
        self.splitter_323.setHandleWidth(0)
        self.main_Fog = QPushButton(self.splitter_323)
        self.main_Fog.setObjectName(u"main_Fog")
        self.splitter_323.addWidget(self.main_Fog)
        self.main_Wind = QPushButton(self.splitter_323)
        self.main_Wind.setObjectName(u"main_Wind")
        self.splitter_323.addWidget(self.main_Wind)
        self.main_Smoke = QPushButton(self.splitter_323)
        self.main_Smoke.setObjectName(u"main_Smoke")
        self.splitter_323.addWidget(self.main_Smoke)
        self.main_Vapour = QPushButton(self.splitter_323)
        self.main_Vapour.setObjectName(u"main_Vapour")
        self.splitter_323.addWidget(self.main_Vapour)
        self.splitter_322.addWidget(self.splitter_323)

        self.gridLayout_2.addWidget(self.splitter_322, 2, 0, 1, 1)


        self.gridLayout.addWidget(self.frame, 0, 0, 1, 1)


        self.retranslateUi(weather_tool)

        QMetaObject.connectSlotsByName(weather_tool)
    # setupUi

    def retranslateUi(self, weather_tool):
        weather_tool.setWindowTitle(QCoreApplication.translate("weather_tool", u"Form", None))
        self.sub_fade_fluctuations.setText(QCoreApplication.translate("weather_tool", u"fade fluctuations", None))
        self.sub_heat_lift.setText(QCoreApplication.translate("weather_tool", u"heat lift", None))
        self.label_161.setText(QCoreApplication.translate("weather_tool", u"weather", None))
        self.pushButton_252.setText(QCoreApplication.translate("weather_tool", u"X", None))
        self.label_162.setText(QCoreApplication.translate("weather_tool", u"sub functions", None))
        self.sub_swirls.setText(QCoreApplication.translate("weather_tool", u"swirls", None))
        self.sub_drift.setText(QCoreApplication.translate("weather_tool", u"drift", None))
        self.sub_gusts.setText(QCoreApplication.translate("weather_tool", u"gusts", None))
        self.sub_density_pulse.setText(QCoreApplication.translate("weather_tool", u"density pulse", None))
        self.main_Fog.setText(QCoreApplication.translate("weather_tool", u"Fog", None))
        self.main_Wind.setText(QCoreApplication.translate("weather_tool", u"Wind ", None))
        self.main_Smoke.setText(QCoreApplication.translate("weather_tool", u"Smoke ", None))
        self.main_Vapour.setText(QCoreApplication.translate("weather_tool", u"Vapour ", None))
    # retranslateUi

