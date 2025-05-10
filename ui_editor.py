# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'editor.ui'
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
from PySide6.QtWidgets import (QApplication, QComboBox, QFrame, QGraphicsView,
    QGridLayout, QHBoxLayout, QLabel, QMainWindow,
    QPushButton, QSizePolicy, QSpacerItem, QVBoxLayout,
    QWidget)

class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        if not MainWindow.objectName():
            MainWindow.setObjectName(u"MainWindow")
        MainWindow.resize(1282, 987)
        self.centralwidget = QWidget(MainWindow)
        self.centralwidget.setObjectName(u"centralwidget")
        self.gridLayout = QGridLayout(self.centralwidget)
        self.gridLayout.setObjectName(u"gridLayout")
        self.horizontalLayout_10 = QHBoxLayout()
        self.horizontalLayout_10.setObjectName(u"horizontalLayout_10")
        self.verticalLayout_9 = QVBoxLayout()
        self.verticalLayout_9.setObjectName(u"verticalLayout_9")
        self.horizontalLayout_6 = QHBoxLayout()
        self.horizontalLayout_6.setObjectName(u"horizontalLayout_6")
        self.frame = QFrame(self.centralwidget)
        self.frame.setObjectName(u"frame")
        self.frame.setEnabled(True)
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.frame.sizePolicy().hasHeightForWidth())
        self.frame.setSizePolicy(sizePolicy)
        self.frame.setMinimumSize(QSize(200, 100))
        self.frame.setFrameShape(QFrame.Shape.StyledPanel)
        self.frame.setFrameShadow(QFrame.Shadow.Sunken)
        self.layoutWidget_2 = QWidget(self.frame)
        self.layoutWidget_2.setObjectName(u"layoutWidget_2")
        self.layoutWidget_2.setGeometry(QRect(11, 11, 651, 81))
        self.verticalLayout_5 = QVBoxLayout(self.layoutWidget_2)
        self.verticalLayout_5.setObjectName(u"verticalLayout_5")
        self.verticalLayout_5.setContentsMargins(0, 0, 0, 0)
        self.horizontalLayout_4 = QHBoxLayout()
        self.horizontalLayout_4.setObjectName(u"horizontalLayout_4")
        self.import_button = QPushButton(self.layoutWidget_2)
        self.import_button.setObjectName(u"import_button")

        self.horizontalLayout_4.addWidget(self.import_button)

        self.save_button = QPushButton(self.layoutWidget_2)
        self.save_button.setObjectName(u"save_button")

        self.horizontalLayout_4.addWidget(self.save_button)

        self.layers_batton = QPushButton(self.layoutWidget_2)
        self.layers_batton.setObjectName(u"layers_batton")

        self.horizontalLayout_4.addWidget(self.layers_batton)

        self.ai_panel = QPushButton(self.layoutWidget_2)
        self.ai_panel.setObjectName(u"ai_panel")

        self.horizontalLayout_4.addWidget(self.ai_panel)

        self.settings = QPushButton(self.layoutWidget_2)
        self.settings.setObjectName(u"settings")

        self.horizontalLayout_4.addWidget(self.settings)

        self.pushButton_16 = QPushButton(self.layoutWidget_2)
        self.pushButton_16.setObjectName(u"pushButton_16")

        self.horizontalLayout_4.addWidget(self.pushButton_16)

        self.horizontalSpacer_14 = QSpacerItem(168, 21, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_4.addItem(self.horizontalSpacer_14)


        self.verticalLayout_5.addLayout(self.horizontalLayout_4)

        self.horizontalLayout_5 = QHBoxLayout()
        self.horizontalLayout_5.setObjectName(u"horizontalLayout_5")
        self.cursor_Button = QPushButton(self.layoutWidget_2)
        self.cursor_Button.setObjectName(u"cursor_Button")
        icon = QIcon()
        icon.addFile(u"icons/mouse-cursor.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.cursor_Button.setIcon(icon)
        self.cursor_Button.setIconSize(QSize(24, 24))

        self.horizontalLayout_5.addWidget(self.cursor_Button)

        self.palette_Button = QPushButton(self.layoutWidget_2)
        self.palette_Button.setObjectName(u"palette_Button")
        icon1 = QIcon()
        icon1.addFile(u"icons/palette.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.palette_Button.setIcon(icon1)
        self.palette_Button.setIconSize(QSize(24, 24))

        self.horizontalLayout_5.addWidget(self.palette_Button)

        self.tools_Button = QPushButton(self.layoutWidget_2)
        self.tools_Button.setObjectName(u"tools_Button")
        icon2 = QIcon()
        icon2.addFile(u"icons/attribution-pencil.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.tools_Button.setIcon(icon2)
        self.tools_Button.setIconSize(QSize(24, 24))

        self.horizontalLayout_5.addWidget(self.tools_Button)

        self.eye_Button = QPushButton(self.layoutWidget_2)
        self.eye_Button.setObjectName(u"eye_Button")
        icon3 = QIcon()
        icon3.addFile(u"icons/eye.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.eye_Button.setIcon(icon3)
        self.eye_Button.setIconSize(QSize(24, 24))

        self.horizontalLayout_5.addWidget(self.eye_Button)

        self.label_7 = QLabel(self.layoutWidget_2)
        self.label_7.setObjectName(u"label_7")
        font = QFont()
        font.setPointSize(10)
        self.label_7.setFont(font)

        self.horizontalLayout_5.addWidget(self.label_7)

        self.comboBox_3 = QComboBox(self.layoutWidget_2)
        self.comboBox_3.setObjectName(u"comboBox_3")
        self.comboBox_3.setMinimumSize(QSize(400, 0))

        self.horizontalLayout_5.addWidget(self.comboBox_3)

        self.horizontalSpacer_15 = QSpacerItem(168, 21, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_5.addItem(self.horizontalSpacer_15)


        self.verticalLayout_5.addLayout(self.horizontalLayout_5)


        self.horizontalLayout_6.addWidget(self.frame)


        self.verticalLayout_9.addLayout(self.horizontalLayout_6)

        self.horizontalLayout_9 = QHBoxLayout()
        self.horizontalLayout_9.setObjectName(u"horizontalLayout_9")
        self.verticalLayout_6 = QVBoxLayout()
        self.verticalLayout_6.setObjectName(u"verticalLayout_6")
        self.frame_5 = QFrame(self.centralwidget)
        self.frame_5.setObjectName(u"frame_5")
        self.frame_5.setFrameShape(QFrame.Shape.StyledPanel)
        self.frame_5.setFrameShadow(QFrame.Shadow.Raised)
        self.verticalLayout_8 = QVBoxLayout(self.frame_5)
        self.verticalLayout_8.setObjectName(u"verticalLayout_8")
        self.verticalLayout_7 = QVBoxLayout()
        self.verticalLayout_7.setObjectName(u"verticalLayout_7")
        self.Cursor = QPushButton(self.frame_5)
        self.Cursor.setObjectName(u"Cursor")
        self.Cursor.setIcon(icon)
        self.Cursor.setIconSize(QSize(24, 24))

        self.verticalLayout_7.addWidget(self.Cursor)

        self.Semicircle = QPushButton(self.frame_5)
        self.Semicircle.setObjectName(u"Semicircle")
        icon4 = QIcon()
        icon4.addFile(u"icons/circle-half-svgrepo-com.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.Semicircle.setIcon(icon4)
        self.Semicircle.setIconSize(QSize(24, 24))

        self.verticalLayout_7.addWidget(self.Semicircle)

        self.Circle = QPushButton(self.frame_5)
        self.Circle.setObjectName(u"Circle")
        icon5 = QIcon()
        icon5.addFile(u"icons/circle.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.Circle.setIcon(icon5)
        self.Circle.setIconSize(QSize(24, 24))

        self.verticalLayout_7.addWidget(self.Circle)

        self.Freeform = QPushButton(self.frame_5)
        self.Freeform.setObjectName(u"Freeform")
        self.Freeform.setIcon(icon2)
        self.Freeform.setIconSize(QSize(24, 24))

        self.verticalLayout_7.addWidget(self.Freeform)

        self.Angle = QPushButton(self.frame_5)
        self.Angle.setObjectName(u"Angle")
        icon6 = QIcon()
        icon6.addFile(u"icons/angle-svgrepo-com.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.Angle.setIcon(icon6)
        self.Angle.setIconSize(QSize(24, 24))

        self.verticalLayout_7.addWidget(self.Angle)

        self.Rounding = QPushButton(self.frame_5)
        self.Rounding.setObjectName(u"Rounding")
        icon7 = QIcon()
        icon7.addFile(u"icons/Border-Corner-Rounded--Streamline-Tabler.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.Rounding.setIcon(icon7)
        self.Rounding.setIconSize(QSize(24, 24))

        self.verticalLayout_7.addWidget(self.Rounding)

        self.by_point = QPushButton(self.frame_5)
        self.by_point.setObjectName(u"by_point")
        icon8 = QIcon()
        icon8.addFile(u"icons/algorithm.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.by_point.setIcon(icon8)
        self.by_point.setIconSize(QSize(24, 24))

        self.verticalLayout_7.addWidget(self.by_point)

        self.Rectangle = QPushButton(self.frame_5)
        self.Rectangle.setObjectName(u"Rectangle")
        icon9 = QIcon()
        icon9.addFile(u"icons/rectangle-svgrepo-com.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.Rectangle.setIcon(icon9)
        self.Rectangle.setIconSize(QSize(24, 24))

        self.verticalLayout_7.addWidget(self.Rectangle)

        self.Join = QPushButton(self.frame_5)
        self.Join.setObjectName(u"Join")
        icon10 = QIcon()
        icon10.addFile(u"icons/link-alt.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.Join.setIcon(icon10)
        self.Join.setIconSize(QSize(24, 24))

        self.verticalLayout_7.addWidget(self.Join)

        self.Cut = QPushButton(self.frame_5)
        self.Cut.setObjectName(u"Cut")
        icon11 = QIcon()
        icon11.addFile(u"icons/cut-svgrepo-com.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.Cut.setIcon(icon11)
        self.Cut.setIconSize(QSize(24, 24))

        self.verticalLayout_7.addWidget(self.Cut)


        self.verticalLayout_8.addLayout(self.verticalLayout_7)

        self.verticalSpacer_2 = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.verticalLayout_8.addItem(self.verticalSpacer_2)


        self.verticalLayout_6.addWidget(self.frame_5)


        self.horizontalLayout_9.addLayout(self.verticalLayout_6)

        self.graphicsView = QGraphicsView(self.centralwidget)
        self.graphicsView.setObjectName(u"graphicsView")
        self.graphicsView.setMinimumSize(QSize(200, 150))

        self.horizontalLayout_9.addWidget(self.graphicsView)


        self.verticalLayout_9.addLayout(self.horizontalLayout_9)


        self.horizontalLayout_10.addLayout(self.verticalLayout_9)

        self.horizontalLayout_7 = QHBoxLayout()
        self.horizontalLayout_7.setObjectName(u"horizontalLayout_7")
        self.frame_4 = QFrame(self.centralwidget)
        self.frame_4.setObjectName(u"frame_4")
        sizePolicy1 = QSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding)
        sizePolicy1.setHorizontalStretch(0)
        sizePolicy1.setVerticalStretch(0)
        sizePolicy1.setHeightForWidth(self.frame_4.sizePolicy().hasHeightForWidth())
        self.frame_4.setSizePolicy(sizePolicy1)
        self.frame_4.setMinimumSize(QSize(250, 50))
        self.frame_4.setFrameShape(QFrame.Shape.StyledPanel)
        self.frame_4.setFrameShadow(QFrame.Shadow.Raised)
        self.gridLayoutWidget = QWidget(self.frame_4)
        self.gridLayoutWidget.setObjectName(u"gridLayoutWidget")
        self.gridLayoutWidget.setGeometry(QRect(210, 0, 41, 41))
        self.gridLayout_3 = QGridLayout(self.gridLayoutWidget)
        self.gridLayout_3.setObjectName(u"gridLayout_3")
        self.gridLayout_3.setContentsMargins(0, 0, 0, 0)
        self.horizontalSpacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.gridLayout_3.addItem(self.horizontalSpacer, 0, 0, 1, 1)

        self.pushButton_17 = QPushButton(self.gridLayoutWidget)
        self.pushButton_17.setObjectName(u"pushButton_17")

        self.gridLayout_3.addWidget(self.pushButton_17, 0, 1, 1, 1)

        self.verticalSpacer = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.gridLayout_3.addItem(self.verticalSpacer, 1, 1, 1, 1)


        self.horizontalLayout_7.addWidget(self.frame_4)


        self.horizontalLayout_10.addLayout(self.horizontalLayout_7)


        self.gridLayout.addLayout(self.horizontalLayout_10, 0, 0, 1, 1)

        MainWindow.setCentralWidget(self.centralwidget)

        self.retranslateUi(MainWindow)

        QMetaObject.connectSlotsByName(MainWindow)
    # setupUi

    def retranslateUi(self, MainWindow):
        MainWindow.setWindowTitle(QCoreApplication.translate("MainWindow", u"MainWindow", None))
        self.import_button.setText(QCoreApplication.translate("MainWindow", u"import", None))
        self.save_button.setText(QCoreApplication.translate("MainWindow", u"save", None))
        self.layers_batton.setText(QCoreApplication.translate("MainWindow", u"Layers panel", None))
        self.ai_panel.setText(QCoreApplication.translate("MainWindow", u"AI panel", None))
        self.settings.setText(QCoreApplication.translate("MainWindow", u"settings", None))
        self.pushButton_16.setText("")
        self.cursor_Button.setText("")
        self.palette_Button.setText("")
        self.tools_Button.setText("")
        self.eye_Button.setText("")
        self.label_7.setText(QCoreApplication.translate("MainWindow", u"object ", None))
        self.Cursor.setText("")
        self.Semicircle.setText("")
        self.Circle.setText("")
        self.Freeform.setText("")
        self.Angle.setText("")
        self.Rounding.setText("")
        self.by_point.setText("")
        self.Rectangle.setText("")
        self.Join.setText("")
        self.Cut.setText("")
        self.pushButton_17.setText(QCoreApplication.translate("MainWindow", u"X", None))
    # retranslateUi

