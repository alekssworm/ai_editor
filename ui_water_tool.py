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
from PySide6.QtWidgets import (QApplication, QFrame, QGridLayout, QGroupBox,
    QLabel, QLayout, QPushButton, QSizePolicy,
    QSpinBox, QSplitter, QWidget)

class Ui_Form(object):
    def setupUi(self, Form):
        if not Form.objectName():
            Form.setObjectName(u"Form")
        Form.resize(278, 432)
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        sizePolicy.setHorizontalStretch(28)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(Form.sizePolicy().hasHeightForWidth())
        Form.setSizePolicy(sizePolicy)
        self.gridLayout = QGridLayout(Form)
        self.gridLayout.setObjectName(u"gridLayout")
        self.frame_7 = QFrame(Form)
        self.frame_7.setObjectName(u"frame_7")
        sizePolicy1 = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        sizePolicy1.setHorizontalStretch(0)
        sizePolicy1.setVerticalStretch(0)
        sizePolicy1.setHeightForWidth(self.frame_7.sizePolicy().hasHeightForWidth())
        self.frame_7.setSizePolicy(sizePolicy1)
        self.frame_7.setMaximumSize(QSize(280, 16777215))
        self.frame_7.setFrameShape(QFrame.Shape.StyledPanel)
        self.frame_7.setFrameShadow(QFrame.Shadow.Raised)
        self.gridLayout_2 = QGridLayout(self.frame_7)
        self.gridLayout_2.setObjectName(u"gridLayout_2")
        self.label_175 = QLabel(self.frame_7)
        self.label_175.setObjectName(u"label_175")
        self.label_175.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.gridLayout_2.addWidget(self.label_175, 0, 0, 1, 1)

        self.pushButton_264 = QPushButton(self.frame_7)
        self.pushButton_264.setObjectName(u"pushButton_264")
        self.pushButton_264.setMaximumSize(QSize(30, 30))

        self.gridLayout_2.addWidget(self.pushButton_264, 0, 1, 1, 1)

        self.splitter_347 = QSplitter(self.frame_7)
        self.splitter_347.setObjectName(u"splitter_347")
        self.splitter_347.setOrientation(Qt.Orientation.Horizontal)
        self.splitter_347.setHandleWidth(0)
        self.pushButton_265 = QPushButton(self.splitter_347)
        self.pushButton_265.setObjectName(u"pushButton_265")
        self.splitter_347.addWidget(self.pushButton_265)
        self.pushButton_266 = QPushButton(self.splitter_347)
        self.pushButton_266.setObjectName(u"pushButton_266")
        self.splitter_347.addWidget(self.pushButton_266)
        self.pushButton_267 = QPushButton(self.splitter_347)
        self.pushButton_267.setObjectName(u"pushButton_267")
        self.splitter_347.addWidget(self.pushButton_267)

        self.gridLayout_2.addWidget(self.splitter_347, 1, 0, 1, 2)

        self.label_176 = QLabel(self.frame_7)
        self.label_176.setObjectName(u"label_176")
        self.label_176.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.gridLayout_2.addWidget(self.label_176, 2, 0, 1, 1)

        self.splitter_2 = QSplitter(self.frame_7)
        self.splitter_2.setObjectName(u"splitter_2")
        self.splitter_2.setOrientation(Qt.Orientation.Vertical)
        self.splitter_2.setHandleWidth(0)
        self.splitter = QSplitter(self.splitter_2)
        self.splitter.setObjectName(u"splitter")
        self.splitter.setOrientation(Qt.Orientation.Horizontal)
        self.splitter.setHandleWidth(0)
        self.pushButton_268 = QPushButton(self.splitter)
        self.pushButton_268.setObjectName(u"pushButton_268")
        self.splitter.addWidget(self.pushButton_268)
        self.pushButton_269 = QPushButton(self.splitter)
        self.pushButton_269.setObjectName(u"pushButton_269")
        self.splitter.addWidget(self.pushButton_269)
        self.pushButton_270 = QPushButton(self.splitter)
        self.pushButton_270.setObjectName(u"pushButton_270")
        self.splitter.addWidget(self.pushButton_270)
        self.splitter_2.addWidget(self.splitter)
        self.splitter_351 = QSplitter(self.splitter_2)
        self.splitter_351.setObjectName(u"splitter_351")
        self.splitter_351.setOrientation(Qt.Orientation.Horizontal)
        self.splitter_351.setHandleWidth(0)
        self.pushButton_271 = QPushButton(self.splitter_351)
        self.pushButton_271.setObjectName(u"pushButton_271")
        self.splitter_351.addWidget(self.pushButton_271)
        self.pushButton_272 = QPushButton(self.splitter_351)
        self.pushButton_272.setObjectName(u"pushButton_272")
        self.splitter_351.addWidget(self.pushButton_272)
        self.pushButton_273 = QPushButton(self.splitter_351)
        self.pushButton_273.setObjectName(u"pushButton_273")
        self.splitter_351.addWidget(self.pushButton_273)
        self.splitter_2.addWidget(self.splitter_351)
        self.splitter_353 = QSplitter(self.splitter_2)
        self.splitter_353.setObjectName(u"splitter_353")
        self.splitter_353.setOrientation(Qt.Orientation.Horizontal)
        self.splitter_353.setHandleWidth(0)
        self.pushButton_274 = QPushButton(self.splitter_353)
        self.pushButton_274.setObjectName(u"pushButton_274")
        self.splitter_353.addWidget(self.pushButton_274)
        self.pushButton_275 = QPushButton(self.splitter_353)
        self.pushButton_275.setObjectName(u"pushButton_275")
        self.splitter_353.addWidget(self.pushButton_275)
        self.pushButton_276 = QPushButton(self.splitter_353)
        self.pushButton_276.setObjectName(u"pushButton_276")
        self.splitter_353.addWidget(self.pushButton_276)
        self.splitter_2.addWidget(self.splitter_353)
        self.splitter_354 = QSplitter(self.splitter_2)
        self.splitter_354.setObjectName(u"splitter_354")
        self.splitter_354.setOrientation(Qt.Orientation.Horizontal)
        self.splitter_354.setHandleWidth(0)
        self.pushButton_277 = QPushButton(self.splitter_354)
        self.pushButton_277.setObjectName(u"pushButton_277")
        self.splitter_354.addWidget(self.pushButton_277)
        self.pushButton_278 = QPushButton(self.splitter_354)
        self.pushButton_278.setObjectName(u"pushButton_278")
        self.splitter_354.addWidget(self.pushButton_278)
        self.pushButton_279 = QPushButton(self.splitter_354)
        self.pushButton_279.setObjectName(u"pushButton_279")
        self.splitter_354.addWidget(self.pushButton_279)
        self.splitter_2.addWidget(self.splitter_354)

        self.gridLayout_2.addWidget(self.splitter_2, 3, 0, 1, 2)

        self.label_177 = QLabel(self.frame_7)
        self.label_177.setObjectName(u"label_177")
        self.label_177.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.gridLayout_2.addWidget(self.label_177, 4, 0, 1, 1)

        self.groupBox_18 = QGroupBox(self.frame_7)
        self.groupBox_18.setObjectName(u"groupBox_18")
        self.groupBox_18.setMaximumSize(QSize(280, 16777215))
        self.gridLayout_58 = QGridLayout(self.groupBox_18)
        self.gridLayout_58.setObjectName(u"gridLayout_58")
        self.gridLayout_58.setSizeConstraint(QLayout.SizeConstraint.SetFixedSize)
        self.splitter_357 = QSplitter(self.groupBox_18)
        self.splitter_357.setObjectName(u"splitter_357")
        self.splitter_357.setOrientation(Qt.Orientation.Horizontal)
        self.splitter_357.setHandleWidth(0)
        self.label_179 = QLabel(self.splitter_357)
        self.label_179.setObjectName(u"label_179")
        self.splitter_357.addWidget(self.label_179)
        self.spinBox_123 = QSpinBox(self.splitter_357)
        self.spinBox_123.setObjectName(u"spinBox_123")
        sizePolicy2 = QSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        sizePolicy2.setHorizontalStretch(0)
        sizePolicy2.setVerticalStretch(0)
        sizePolicy2.setHeightForWidth(self.spinBox_123.sizePolicy().hasHeightForWidth())
        self.spinBox_123.setSizePolicy(sizePolicy2)
        self.spinBox_123.setMinimumSize(QSize(100, 0))
        self.spinBox_123.setMaximumSize(QSize(120, 16777215))
        self.splitter_357.addWidget(self.spinBox_123)

        self.gridLayout_58.addWidget(self.splitter_357, 5, 0, 1, 1)

        self.splitter_360 = QSplitter(self.groupBox_18)
        self.splitter_360.setObjectName(u"splitter_360")
        self.splitter_360.setOrientation(Qt.Orientation.Horizontal)
        self.splitter_360.setHandleWidth(0)
        self.label_182 = QLabel(self.splitter_360)
        self.label_182.setObjectName(u"label_182")
        self.splitter_360.addWidget(self.label_182)
        self.spinBox_126 = QSpinBox(self.splitter_360)
        self.spinBox_126.setObjectName(u"spinBox_126")
        self.splitter_360.addWidget(self.spinBox_126)

        self.gridLayout_58.addWidget(self.splitter_360, 3, 0, 1, 1)

        self.splitter_356 = QSplitter(self.groupBox_18)
        self.splitter_356.setObjectName(u"splitter_356")
        self.splitter_356.setOrientation(Qt.Orientation.Horizontal)
        self.splitter_356.setHandleWidth(0)
        self.label_178 = QLabel(self.splitter_356)
        self.label_178.setObjectName(u"label_178")
        self.splitter_356.addWidget(self.label_178)
        self.spinBox_122 = QSpinBox(self.splitter_356)
        self.spinBox_122.setObjectName(u"spinBox_122")
        self.splitter_356.addWidget(self.spinBox_122)

        self.gridLayout_58.addWidget(self.splitter_356, 2, 0, 1, 1)

        self.splitter_359 = QSplitter(self.groupBox_18)
        self.splitter_359.setObjectName(u"splitter_359")
        self.splitter_359.setOrientation(Qt.Orientation.Horizontal)
        self.splitter_359.setHandleWidth(0)
        self.label_181 = QLabel(self.splitter_359)
        self.label_181.setObjectName(u"label_181")
        self.splitter_359.addWidget(self.label_181)
        self.spinBox_125 = QSpinBox(self.splitter_359)
        self.spinBox_125.setObjectName(u"spinBox_125")
        sizePolicy2.setHeightForWidth(self.spinBox_125.sizePolicy().hasHeightForWidth())
        self.spinBox_125.setSizePolicy(sizePolicy2)
        self.spinBox_125.setMinimumSize(QSize(100, 0))
        self.spinBox_125.setMaximumSize(QSize(120, 16777215))
        self.splitter_359.addWidget(self.spinBox_125)

        self.gridLayout_58.addWidget(self.splitter_359, 4, 0, 1, 1)

        self.pushButton_280 = QPushButton(self.groupBox_18)
        self.pushButton_280.setObjectName(u"pushButton_280")

        self.gridLayout_58.addWidget(self.pushButton_280, 6, 0, 1, 1)

        self.splitter_358 = QSplitter(self.groupBox_18)
        self.splitter_358.setObjectName(u"splitter_358")
        self.splitter_358.setOrientation(Qt.Orientation.Horizontal)
        self.splitter_358.setHandleWidth(0)
        self.label_180 = QLabel(self.splitter_358)
        self.label_180.setObjectName(u"label_180")
        self.splitter_358.addWidget(self.label_180)
        self.spinBox_124 = QSpinBox(self.splitter_358)
        self.spinBox_124.setObjectName(u"spinBox_124")
        self.splitter_358.addWidget(self.spinBox_124)

        self.gridLayout_58.addWidget(self.splitter_358, 1, 0, 1, 1)


        self.gridLayout_2.addWidget(self.groupBox_18, 5, 0, 1, 2)


        self.gridLayout.addWidget(self.frame_7, 0, 0, 1, 1)


        self.retranslateUi(Form)

        QMetaObject.connectSlotsByName(Form)
    # setupUi

    def retranslateUi(self, Form):
        Form.setWindowTitle(QCoreApplication.translate("Form", u"Form", None))
        self.label_175.setText(QCoreApplication.translate("Form", u"water", None))
        self.pushButton_264.setText(QCoreApplication.translate("Form", u"X", None))
        self.pushButton_265.setText(QCoreApplication.translate("Form", u"waterfall", None))
        self.pushButton_266.setText(QCoreApplication.translate("Form", u"river", None))
        self.pushButton_267.setText(QCoreApplication.translate("Form", u"Still water", None))
        self.label_176.setText(QCoreApplication.translate("Form", u"sub functions", None))
        self.pushButton_268.setText(QCoreApplication.translate("Form", u"waves", None))
        self.pushButton_269.setText(QCoreApplication.translate("Form", u"ripples", None))
        self.pushButton_270.setText(QCoreApplication.translate("Form", u"splashes", None))
        self.pushButton_271.setText(QCoreApplication.translate("Form", u"Bubbles", None))
        self.pushButton_272.setText(QCoreApplication.translate("Form", u"reflections", None))
        self.pushButton_273.setText(QCoreApplication.translate("Form", u"Sediment", None))
        self.pushButton_274.setText(QCoreApplication.translate("Form", u"foam", None))
        self.pushButton_275.setText(QCoreApplication.translate("Form", u"transparency", None))
        self.pushButton_276.setText(QCoreApplication.translate("Form", u"viscosity", None))
        self.pushButton_277.setText(QCoreApplication.translate("Form", u"wet edge", None))
        self.pushButton_278.setText(QCoreApplication.translate("Form", u"caustics ", None))
        self.pushButton_279.setText(QCoreApplication.translate("Form", u"distortion", None))
        self.label_177.setText(QCoreApplication.translate("Form", u"setings", None))
        self.groupBox_18.setTitle("")
        self.label_179.setText(QCoreApplication.translate("Form", u"grain             ", None))
        self.label_182.setText(QCoreApplication.translate("Form", u"opacity", None))
        self.label_178.setText(QCoreApplication.translate("Form", u"intensity ", None))
        self.label_181.setText(QCoreApplication.translate("Form", u"randomness        ", None))
        self.pushButton_280.setText(QCoreApplication.translate("Form", u"color", None))
        self.label_180.setText(QCoreApplication.translate("Form", u"power", None))
    # retranslateUi

