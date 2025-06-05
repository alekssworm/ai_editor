# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'fire_tool.ui'
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

class Ui_fire_tool(object):
    def setupUi(self, fire_tool):
        if not fire_tool.objectName():
            fire_tool.setObjectName(u"fire_tool")
        fire_tool.resize(280, 192)
        fire_tool.setMaximumSize(QSize(280, 16777215))
        self.gridLayout_3 = QGridLayout(fire_tool)
        self.gridLayout_3.setObjectName(u"gridLayout_3")
        self.frame = QFrame(fire_tool)
        self.frame.setObjectName(u"frame")
        self.frame.setEnabled(True)
        self.frame.setMaximumSize(QSize(280, 16777215))
        self.frame.setFrameShape(QFrame.Shape.StyledPanel)
        self.frame.setFrameShadow(QFrame.Shadow.Raised)
        self.gridLayout_2 = QGridLayout(self.frame)
        self.gridLayout_2.setObjectName(u"gridLayout_2")
        self.label_184 = QLabel(self.frame)
        self.label_184.setObjectName(u"label_184")
        self.label_184.setMaximumSize(QSize(280, 16777215))
        self.label_184.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.gridLayout_2.addWidget(self.label_184, 3, 0, 1, 1)

        self.splitter_3 = QSplitter(self.frame)
        self.splitter_3.setObjectName(u"splitter_3")
        self.splitter_3.setOrientation(Qt.Orientation.Vertical)
        self.splitter_3.setHandleWidth(0)
        self.splitter_368 = QSplitter(self.splitter_3)
        self.splitter_368.setObjectName(u"splitter_368")
        self.splitter_368.setOrientation(Qt.Orientation.Horizontal)
        self.splitter_368.setHandleWidth(0)
        self.sub_sparks = QPushButton(self.splitter_368)
        self.sub_sparks.setObjectName(u"sub_sparks")
        self.splitter_368.addWidget(self.sub_sparks)
        self.sub_smoke = QPushButton(self.splitter_368)
        self.sub_smoke.setObjectName(u"sub_smoke")
        self.splitter_368.addWidget(self.sub_smoke)
        self.splitter_3.addWidget(self.splitter_368)
        self.splitter_369 = QSplitter(self.splitter_3)
        self.splitter_369.setObjectName(u"splitter_369")
        self.splitter_369.setOrientation(Qt.Orientation.Horizontal)
        self.splitter_369.setHandleWidth(0)
        self.sub_heat_distortion = QPushButton(self.splitter_369)
        self.sub_heat_distortion.setObjectName(u"sub_heat_distortion")
        self.splitter_369.addWidget(self.sub_heat_distortion)
        self.sub_pulse = QPushButton(self.splitter_369)
        self.sub_pulse.setObjectName(u"sub_pulse")
        self.splitter_369.addWidget(self.sub_pulse)
        self.splitter_3.addWidget(self.splitter_369)
        self.splitter_371 = QSplitter(self.splitter_3)
        self.splitter_371.setObjectName(u"splitter_371")
        self.splitter_371.setOrientation(Qt.Orientation.Horizontal)
        self.splitter_371.setHandleWidth(0)
        self.sub_shadow_flicker = QPushButton(self.splitter_371)
        self.sub_shadow_flicker.setObjectName(u"sub_shadow_flicker")
        self.splitter_371.addWidget(self.sub_shadow_flicker)
        self.sub_light_glow = QPushButton(self.splitter_371)
        self.sub_light_glow.setObjectName(u"sub_light_glow")
        self.splitter_371.addWidget(self.sub_light_glow)
        self.splitter_3.addWidget(self.splitter_371)

        self.gridLayout_2.addWidget(self.splitter_3, 5, 0, 1, 1)

        self.splitter_2 = QSplitter(self.frame)
        self.splitter_2.setObjectName(u"splitter_2")
        self.splitter_2.setOrientation(Qt.Orientation.Horizontal)
        self.splitter_2.setHandleWidth(0)
        self.main_Campfire = QPushButton(self.splitter_2)
        self.main_Campfire.setObjectName(u"main_Campfire")
        self.splitter_2.addWidget(self.main_Campfire)
        self.main_Torch = QPushButton(self.splitter_2)
        self.main_Torch.setObjectName(u"main_Torch")
        self.splitter_2.addWidget(self.main_Torch)
        self.main_Candle = QPushButton(self.splitter_2)
        self.main_Candle.setObjectName(u"main_Candle")
        self.splitter_2.addWidget(self.main_Candle)
        self.main_Lava = QPushButton(self.splitter_2)
        self.main_Lava.setObjectName(u"main_Lava")
        self.splitter_2.addWidget(self.main_Lava)

        self.gridLayout_2.addWidget(self.splitter_2, 2, 0, 1, 1)

        self.splitter = QSplitter(self.frame)
        self.splitter.setObjectName(u"splitter")
        self.splitter.setOrientation(Qt.Orientation.Horizontal)
        self.splitter.setHandleWidth(0)
        self.label_183 = QLabel(self.splitter)
        self.label_183.setObjectName(u"label_183")
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.label_183.sizePolicy().hasHeightForWidth())
        self.label_183.setSizePolicy(sizePolicy)
        self.label_183.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.splitter.addWidget(self.label_183)
        self.pushButton_281 = QPushButton(self.splitter)
        self.pushButton_281.setObjectName(u"pushButton_281")
        sizePolicy1 = QSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        sizePolicy1.setHorizontalStretch(0)
        sizePolicy1.setVerticalStretch(0)
        sizePolicy1.setHeightForWidth(self.pushButton_281.sizePolicy().hasHeightForWidth())
        self.pushButton_281.setSizePolicy(sizePolicy1)
        self.pushButton_281.setMaximumSize(QSize(30, 30))
        self.splitter.addWidget(self.pushButton_281)

        self.gridLayout_2.addWidget(self.splitter, 1, 0, 1, 1)


        self.gridLayout_3.addWidget(self.frame, 0, 0, 1, 1)


        self.retranslateUi(fire_tool)

        QMetaObject.connectSlotsByName(fire_tool)
    # setupUi

    def retranslateUi(self, fire_tool):
        fire_tool.setWindowTitle(QCoreApplication.translate("fire_tool", u"Form", None))
        self.label_184.setText(QCoreApplication.translate("fire_tool", u"sub functions", None))
        self.sub_sparks.setText(QCoreApplication.translate("fire_tool", u"sparks", None))
        self.sub_smoke.setText(QCoreApplication.translate("fire_tool", u"smoke", None))
        self.sub_heat_distortion.setText(QCoreApplication.translate("fire_tool", u"heat distortion", None))
        self.sub_pulse.setText(QCoreApplication.translate("fire_tool", u"pulse", None))
        self.sub_shadow_flicker.setText(QCoreApplication.translate("fire_tool", u"shadow flicker", None))
        self.sub_light_glow.setText(QCoreApplication.translate("fire_tool", u"light glow", None))
        self.main_Campfire.setText(QCoreApplication.translate("fire_tool", u"Campfire ", None))
        self.main_Torch.setText(QCoreApplication.translate("fire_tool", u"Torch ", None))
        self.main_Candle.setText(QCoreApplication.translate("fire_tool", u"Candle ", None))
        self.main_Lava.setText(QCoreApplication.translate("fire_tool", u"Lava ", None))
        self.label_183.setText(QCoreApplication.translate("fire_tool", u"fire", None))
        self.pushButton_281.setText(QCoreApplication.translate("fire_tool", u"X", None))
    # retranslateUi

