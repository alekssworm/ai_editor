# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'water_tool.ui'
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

class Ui_water_tool(object):
    def setupUi(self, water_tool):
        if not water_tool.objectName():
            water_tool.setObjectName(u"water_tool")
        water_tool.resize(278, 216)
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        sizePolicy.setHorizontalStretch(28)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(water_tool.sizePolicy().hasHeightForWidth())
        water_tool.setSizePolicy(sizePolicy)
        self.gridLayout = QGridLayout(water_tool)
        self.gridLayout.setObjectName(u"gridLayout")
        self.frame_7 = QFrame(water_tool)
        self.frame_7.setObjectName(u"frame_7")
        sizePolicy1 = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        sizePolicy1.setHorizontalStretch(0)
        sizePolicy1.setVerticalStretch(0)
        sizePolicy1.setHeightForWidth(self.frame_7.sizePolicy().hasHeightForWidth())
        self.frame_7.setSizePolicy(sizePolicy1)
        self.frame_7.setMaximumSize(QSize(280, 16777215))
        self.frame_7.setFrameShape(QFrame.Shape.StyledPanel)
        self.frame_7.setFrameShadow(QFrame.Shadow.Raised)
        self.gridLayout_3 = QGridLayout(self.frame_7)
        self.gridLayout_3.setObjectName(u"gridLayout_3")
        self.splitter_347 = QSplitter(self.frame_7)
        self.splitter_347.setObjectName(u"splitter_347")
        self.splitter_347.setOrientation(Qt.Orientation.Horizontal)
        self.splitter_347.setHandleWidth(0)
        self.main_waterfall = QPushButton(self.splitter_347)
        self.main_waterfall.setObjectName(u"main_waterfall")
        self.splitter_347.addWidget(self.main_waterfall)
        self.main_river = QPushButton(self.splitter_347)
        self.main_river.setObjectName(u"main_river")
        self.splitter_347.addWidget(self.main_river)
        self.main_Still_water = QPushButton(self.splitter_347)
        self.main_Still_water.setObjectName(u"main_Still_water")
        self.splitter_347.addWidget(self.main_Still_water)

        self.gridLayout_3.addWidget(self.splitter_347, 1, 0, 1, 2)

        self.pushButton_264 = QPushButton(self.frame_7)
        self.pushButton_264.setObjectName(u"pushButton_264")
        self.pushButton_264.setMaximumSize(QSize(30, 30))

        self.gridLayout_3.addWidget(self.pushButton_264, 0, 1, 1, 1)

        self.splitter_2 = QSplitter(self.frame_7)
        self.splitter_2.setObjectName(u"splitter_2")
        self.splitter_2.setOrientation(Qt.Orientation.Vertical)
        self.splitter_2.setHandleWidth(0)
        self.splitter = QSplitter(self.splitter_2)
        self.splitter.setObjectName(u"splitter")
        self.splitter.setOrientation(Qt.Orientation.Horizontal)
        self.splitter.setHandleWidth(0)
        self.sub_waves = QPushButton(self.splitter)
        self.sub_waves.setObjectName(u"sub_waves")
        self.splitter.addWidget(self.sub_waves)
        self.sub_ripples = QPushButton(self.splitter)
        self.sub_ripples.setObjectName(u"sub_ripples")
        self.splitter.addWidget(self.sub_ripples)
        self.sub_splashes = QPushButton(self.splitter)
        self.sub_splashes.setObjectName(u"sub_splashes")
        self.splitter.addWidget(self.sub_splashes)
        self.splitter_2.addWidget(self.splitter)
        self.splitter_351 = QSplitter(self.splitter_2)
        self.splitter_351.setObjectName(u"splitter_351")
        self.splitter_351.setOrientation(Qt.Orientation.Horizontal)
        self.splitter_351.setHandleWidth(0)
        self.sub_Bubbles = QPushButton(self.splitter_351)
        self.sub_Bubbles.setObjectName(u"sub_Bubbles")
        self.splitter_351.addWidget(self.sub_Bubbles)
        self.sub_reflections = QPushButton(self.splitter_351)
        self.sub_reflections.setObjectName(u"sub_reflections")
        self.splitter_351.addWidget(self.sub_reflections)
        self.sub_Sediment = QPushButton(self.splitter_351)
        self.sub_Sediment.setObjectName(u"sub_Sediment")
        self.splitter_351.addWidget(self.sub_Sediment)
        self.splitter_2.addWidget(self.splitter_351)
        self.splitter_353 = QSplitter(self.splitter_2)
        self.splitter_353.setObjectName(u"splitter_353")
        self.splitter_353.setOrientation(Qt.Orientation.Horizontal)
        self.splitter_353.setHandleWidth(0)
        self.sub_foam = QPushButton(self.splitter_353)
        self.sub_foam.setObjectName(u"sub_foam")
        self.splitter_353.addWidget(self.sub_foam)
        self.sub_transparency = QPushButton(self.splitter_353)
        self.sub_transparency.setObjectName(u"sub_transparency")
        self.splitter_353.addWidget(self.sub_transparency)
        self.sub_viscosity = QPushButton(self.splitter_353)
        self.sub_viscosity.setObjectName(u"sub_viscosity")
        self.splitter_353.addWidget(self.sub_viscosity)
        self.splitter_2.addWidget(self.splitter_353)
        self.splitter_354 = QSplitter(self.splitter_2)
        self.splitter_354.setObjectName(u"splitter_354")
        self.splitter_354.setOrientation(Qt.Orientation.Horizontal)
        self.splitter_354.setHandleWidth(0)
        self.sub_wet_edge = QPushButton(self.splitter_354)
        self.sub_wet_edge.setObjectName(u"sub_wet_edge")
        self.splitter_354.addWidget(self.sub_wet_edge)
        self.sub_caustics = QPushButton(self.splitter_354)
        self.sub_caustics.setObjectName(u"sub_caustics")
        self.splitter_354.addWidget(self.sub_caustics)
        self.sub_distortion = QPushButton(self.splitter_354)
        self.sub_distortion.setObjectName(u"sub_distortion")
        self.splitter_354.addWidget(self.sub_distortion)
        self.splitter_2.addWidget(self.splitter_354)

        self.gridLayout_3.addWidget(self.splitter_2, 3, 0, 1, 2)

        self.label_175 = QLabel(self.frame_7)
        self.label_175.setObjectName(u"label_175")
        self.label_175.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.gridLayout_3.addWidget(self.label_175, 0, 0, 1, 1)

        self.label_176 = QLabel(self.frame_7)
        self.label_176.setObjectName(u"label_176")
        self.label_176.setMaximumSize(QSize(280, 16777215))
        self.label_176.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.gridLayout_3.addWidget(self.label_176, 2, 0, 1, 1)


        self.gridLayout.addWidget(self.frame_7, 0, 0, 1, 1)


        self.retranslateUi(water_tool)

        QMetaObject.connectSlotsByName(water_tool)
    # setupUi

    def retranslateUi(self, water_tool):
        water_tool.setWindowTitle(QCoreApplication.translate("water_tool", u"Form", None))
        self.main_waterfall.setText(QCoreApplication.translate("water_tool", u"waterfall", None))
        self.main_river.setText(QCoreApplication.translate("water_tool", u"river", None))
        self.main_Still_water.setText(QCoreApplication.translate("water_tool", u"Still water", None))
        self.pushButton_264.setText(QCoreApplication.translate("water_tool", u"X", None))
        self.sub_waves.setText(QCoreApplication.translate("water_tool", u"waves", None))
        self.sub_ripples.setText(QCoreApplication.translate("water_tool", u"ripples", None))
        self.sub_splashes.setText(QCoreApplication.translate("water_tool", u"splashes", None))
        self.sub_Bubbles.setText(QCoreApplication.translate("water_tool", u"Bubbles", None))
        self.sub_reflections.setText(QCoreApplication.translate("water_tool", u"reflections", None))
        self.sub_Sediment.setText(QCoreApplication.translate("water_tool", u"Sediment", None))
        self.sub_foam.setText(QCoreApplication.translate("water_tool", u"foam", None))
        self.sub_transparency.setText(QCoreApplication.translate("water_tool", u"transparency", None))
        self.sub_viscosity.setText(QCoreApplication.translate("water_tool", u"viscosity", None))
        self.sub_wet_edge.setText(QCoreApplication.translate("water_tool", u"wet edge", None))
        self.sub_caustics.setText(QCoreApplication.translate("water_tool", u"caustics ", None))
        self.sub_distortion.setText(QCoreApplication.translate("water_tool", u"distortion", None))
        self.label_175.setText(QCoreApplication.translate("water_tool", u"water", None))
        self.label_176.setText(QCoreApplication.translate("water_tool", u"sub functions", None))
    # retranslateUi

