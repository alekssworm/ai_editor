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
    QGridLayout, QHBoxLayout, QLabel, QListWidget,
    QListWidgetItem, QMainWindow, QPushButton, QSizePolicy,
    QSpacerItem, QVBoxLayout, QWidget)

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
        self.layoutWidget_2.setGeometry(QRect(11, 11, 705, 81))
        self.verticalLayout_5 = QVBoxLayout(self.layoutWidget_2)
        self.verticalLayout_5.setObjectName(u"verticalLayout_5")
        self.verticalLayout_5.setContentsMargins(0, 0, 0, 0)
        self.horizontalLayout_4 = QHBoxLayout()
        self.horizontalLayout_4.setObjectName(u"horizontalLayout_4")
        self.import_button = QPushButton(self.layoutWidget_2)
        self.import_button.setObjectName(u"import_button")

        self.horizontalLayout_4.addWidget(self.import_button)

        self.import_sceen = QPushButton(self.layoutWidget_2)
        self.import_sceen.setObjectName(u"import_sceen")

        self.horizontalLayout_4.addWidget(self.import_sceen)

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

        self.horizontalSpacer_14 = QSpacerItem(168, 21, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_4.addItem(self.horizontalSpacer_14)


        self.verticalLayout_5.addLayout(self.horizontalLayout_4)

        self.horizontalLayout_5 = QHBoxLayout()
        self.horizontalLayout_5.setObjectName(u"horizontalLayout_5")
        self.cursor_Button = QPushButton(self.layoutWidget_2)
        self.cursor_Button.setObjectName(u"cursor_Button")
        self.cursor_Button.setStyleSheet(u"QPushButton {\n"
"    background-color: #3c3c3c;\n"
"    border-top: 1px solid #4a4a4a;\n"
"    border-left: 1px solid #4a4a4a;\n"
"    border-right: 1px solid #4a4a4a;\n"
"    border-bottom: 1px solid #5b5b5b;\n"
"    border-radius: 6px;\n"
"    padding: 3px;\n"
"}\n"
"\n"
"QPushButton:hover {\n"
"    background-color: #444444;\n"
"}\n"
"\n"
"QPushButton:pressed {\n"
"    background-color: #2f2f2f;\n"
"}\n"
"")
        icon = QIcon()
        icon.addFile(u"icons/mouse-cursor.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.cursor_Button.setIcon(icon)
        self.cursor_Button.setIconSize(QSize(24, 24))

        self.horizontalLayout_5.addWidget(self.cursor_Button)

        self.palette_Button = QPushButton(self.layoutWidget_2)
        self.palette_Button.setObjectName(u"palette_Button")
        self.palette_Button.setStyleSheet(u"QPushButton {\n"
"    background-color: #3c3c3c;\n"
"    border-top: 1px solid #4a4a4a;\n"
"    border-left: 1px solid #4a4a4a;\n"
"    border-right: 1px solid #4a4a4a;\n"
"    border-bottom: 1px solid #5b5b5b;\n"
"    border-radius: 6px;\n"
"    padding: 3px;\n"
"}\n"
"\n"
"QPushButton:hover {\n"
"    background-color: #444444;\n"
"}\n"
"\n"
"QPushButton:pressed {\n"
"    background-color: #2f2f2f;\n"
"}\n"
"")
        icon1 = QIcon()
        icon1.addFile(u"icons/palette.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.palette_Button.setIcon(icon1)
        self.palette_Button.setIconSize(QSize(24, 24))

        self.horizontalLayout_5.addWidget(self.palette_Button)

        self.tools_Button = QPushButton(self.layoutWidget_2)
        self.tools_Button.setObjectName(u"tools_Button")
        self.tools_Button.setStyleSheet(u"QPushButton {\n"
"    background-color: #3c3c3c;\n"
"    border-top: 1px solid #4a4a4a;\n"
"    border-left: 1px solid #4a4a4a;\n"
"    border-right: 1px solid #4a4a4a;\n"
"    border-bottom: 1px solid #5b5b5b;\n"
"    border-radius: 6px;\n"
"    padding: 3px;\n"
"}\n"
"\n"
"QPushButton:hover {\n"
"    background-color: #444444;\n"
"}\n"
"\n"
"QPushButton:pressed {\n"
"    background-color: #2f2f2f;\n"
"}\n"
"")
        icon2 = QIcon()
        icon2.addFile(u"icons/attribution-pencil.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.tools_Button.setIcon(icon2)
        self.tools_Button.setIconSize(QSize(24, 24))

        self.horizontalLayout_5.addWidget(self.tools_Button)

        self.eye_Button = QPushButton(self.layoutWidget_2)
        self.eye_Button.setObjectName(u"eye_Button")
        self.eye_Button.setStyleSheet(u"QPushButton {\n"
"    background-color: #3c3c3c;\n"
"    border-top: 1px solid #4a4a4a;\n"
"    border-left: 1px solid #4a4a4a;\n"
"    border-right: 1px solid #4a4a4a;\n"
"    border-bottom: 1px solid #5b5b5b;\n"
"    border-radius: 6px;\n"
"    padding: 3px;\n"
"}\n"
"\n"
"QPushButton:hover {\n"
"    background-color: #444444;\n"
"}\n"
"\n"
"QPushButton:pressed {\n"
"    background-color: #2f2f2f;\n"
"}\n"
"")
        icon3 = QIcon()
        icon3.addFile(u"icons/eye.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.eye_Button.setIcon(icon3)
        self.eye_Button.setIconSize(QSize(24, 24))

        self.horizontalLayout_5.addWidget(self.eye_Button)

        self.Resizable_button = QPushButton(self.layoutWidget_2)
        self.Resizable_button.setObjectName(u"Resizable_button")
        self.Resizable_button.setStyleSheet(u"QPushButton {\n"
"    background-color: #3c3c3c;\n"
"    border-top: 1px solid #4a4a4a;\n"
"    border-left: 1px solid #4a4a4a;\n"
"    border-right: 1px solid #4a4a4a;\n"
"    border-bottom: 1px solid #5b5b5b;\n"
"    border-radius: 6px;\n"
"    padding: 3px;\n"
"}\n"
"\n"
"QPushButton:hover {\n"
"    background-color: #444444;\n"
"}\n"
"\n"
"QPushButton:pressed {\n"
"    background-color: #2f2f2f;\n"
"}\n"
"")
        icon4 = QIcon()
        icon4.addFile(u"icons/swipe-to-right-svgrepo-com.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.Resizable_button.setIcon(icon4)
        self.Resizable_button.setIconSize(QSize(24, 24))

        self.horizontalLayout_5.addWidget(self.Resizable_button)

        self.label_7 = QLabel(self.layoutWidget_2)
        self.label_7.setObjectName(u"label_7")
        font = QFont()
        font.setPointSize(10)
        self.label_7.setFont(font)

        self.horizontalLayout_5.addWidget(self.label_7)

        self.comboBox_3 = QComboBox(self.layoutWidget_2)
        self.comboBox_3.setObjectName(u"comboBox_3")
        self.comboBox_3.setMinimumSize(QSize(220, 0))

        self.horizontalLayout_5.addWidget(self.comboBox_3)

        self.horizontalSpacer_15 = QSpacerItem(168, 21, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_5.addItem(self.horizontalSpacer_15)


        self.verticalLayout_5.addLayout(self.horizontalLayout_5)

        self.label_8 = QLabel(self.frame)
        self.label_8.setObjectName(u"label_8")
        self.label_8.setGeometry(QRect(950, 80, 49, 16))

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
        self.Cursor.setStyleSheet(u"QPushButton {\n"
"    background-color: #3c3c3c;\n"
"    border-top: 1px solid #4a4a4a;\n"
"    border-left: 1px solid #4a4a4a;\n"
"    border-right: 1px solid #4a4a4a;\n"
"    border-bottom: 1px solid #5b5b5b;\n"
"    border-radius: 6px;\n"
"    padding: 3px;\n"
"}\n"
"\n"
"QPushButton:hover {\n"
"    background-color: #444444;\n"
"}\n"
"\n"
"QPushButton:pressed {\n"
"    background-color: #2f2f2f;\n"
"}\n"
"\n"
"")
        self.Cursor.setIcon(icon)
        self.Cursor.setIconSize(QSize(24, 24))

        self.verticalLayout_7.addWidget(self.Cursor)

        self.Semicircle = QPushButton(self.frame_5)
        self.Semicircle.setObjectName(u"Semicircle")
        self.Semicircle.setStyleSheet(u"QPushButton {\n"
"    background-color: #3c3c3c;\n"
"    border-top: 1px solid #4a4a4a;\n"
"    border-left: 1px solid #4a4a4a;\n"
"    border-right: 1px solid #4a4a4a;\n"
"    border-bottom: 1px solid #5b5b5b;\n"
"    border-radius: 6px;\n"
"    padding: 3px;\n"
"}\n"
"\n"
"QPushButton:hover {\n"
"    background-color: #444444;\n"
"}\n"
"\n"
"QPushButton:pressed {\n"
"    background-color: #2f2f2f;\n"
"}\n"
"\n"
"")
        icon5 = QIcon()
        icon5.addFile(u"icons/circle-half-svgrepo-com.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.Semicircle.setIcon(icon5)
        self.Semicircle.setIconSize(QSize(24, 24))

        self.verticalLayout_7.addWidget(self.Semicircle)

        self.Circle = QPushButton(self.frame_5)
        self.Circle.setObjectName(u"Circle")
        self.Circle.setStyleSheet(u"QPushButton {\n"
"    background-color: #3c3c3c;\n"
"    border-top: 1px solid #4a4a4a;\n"
"    border-left: 1px solid #4a4a4a;\n"
"    border-right: 1px solid #4a4a4a;\n"
"    border-bottom: 1px solid #5b5b5b;\n"
"    border-radius: 6px;\n"
"    padding: 3px;\n"
"}\n"
"\n"
"QPushButton:hover {\n"
"    background-color: #444444;\n"
"}\n"
"\n"
"QPushButton:pressed {\n"
"    background-color: #2f2f2f;\n"
"}\n"
"\n"
"")
        icon6 = QIcon()
        icon6.addFile(u"icons/circle.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.Circle.setIcon(icon6)
        self.Circle.setIconSize(QSize(24, 24))

        self.verticalLayout_7.addWidget(self.Circle)

        self.Freeform = QPushButton(self.frame_5)
        self.Freeform.setObjectName(u"Freeform")
        self.Freeform.setStyleSheet(u"QPushButton {\n"
"    background-color: #3c3c3c;\n"
"    border-top: 1px solid #4a4a4a;\n"
"    border-left: 1px solid #4a4a4a;\n"
"    border-right: 1px solid #4a4a4a;\n"
"    border-bottom: 1px solid #5b5b5b;\n"
"    border-radius: 6px;\n"
"    padding: 3px;\n"
"}\n"
"\n"
"QPushButton:hover {\n"
"    background-color: #444444;\n"
"}\n"
"\n"
"QPushButton:pressed {\n"
"    background-color: #2f2f2f;\n"
"}\n"
"")
        self.Freeform.setIcon(icon2)
        self.Freeform.setIconSize(QSize(24, 24))

        self.verticalLayout_7.addWidget(self.Freeform)

        self.Angle = QPushButton(self.frame_5)
        self.Angle.setObjectName(u"Angle")
        self.Angle.setStyleSheet(u"QPushButton {\n"
"    background-color: #3c3c3c;\n"
"    border-top: 1px solid #4a4a4a;\n"
"    border-left: 1px solid #4a4a4a;\n"
"    border-right: 1px solid #4a4a4a;\n"
"    border-bottom: 1px solid #5b5b5b;\n"
"    border-radius: 6px;\n"
"    padding: 3px;\n"
"}\n"
"\n"
"QPushButton:hover {\n"
"    background-color: #444444;\n"
"}\n"
"\n"
"QPushButton:pressed {\n"
"    background-color: #2f2f2f;\n"
"}\n"
"\n"
"")
        icon7 = QIcon()
        icon7.addFile(u"icons/angle-svgrepo-com.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.Angle.setIcon(icon7)
        self.Angle.setIconSize(QSize(24, 24))

        self.verticalLayout_7.addWidget(self.Angle)

        self.Rounding = QPushButton(self.frame_5)
        self.Rounding.setObjectName(u"Rounding")
        self.Rounding.setStyleSheet(u"QPushButton {\n"
"    background-color: #3c3c3c;\n"
"    border-top: 1px solid #4a4a4a;\n"
"    border-left: 1px solid #4a4a4a;\n"
"    border-right: 1px solid #4a4a4a;\n"
"    border-bottom: 1px solid #5b5b5b;\n"
"    border-radius: 6px;\n"
"    padding: 3px;\n"
"}\n"
"\n"
"QPushButton:hover {\n"
"    background-color: #444444;\n"
"}\n"
"\n"
"QPushButton:pressed {\n"
"    background-color: #2f2f2f;\n"
"}\n"
"")
        icon8 = QIcon()
        icon8.addFile(u"icons/Border-Corner-Rounded--Streamline-Tabler.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.Rounding.setIcon(icon8)
        self.Rounding.setIconSize(QSize(24, 24))

        self.verticalLayout_7.addWidget(self.Rounding)

        self.by_point = QPushButton(self.frame_5)
        self.by_point.setObjectName(u"by_point")
        self.by_point.setStyleSheet(u"QPushButton {\n"
"    background-color: #3c3c3c;\n"
"    border-top: 1px solid #4a4a4a;\n"
"    border-left: 1px solid #4a4a4a;\n"
"    border-right: 1px solid #4a4a4a;\n"
"    border-bottom: 1px solid #5b5b5b;\n"
"    border-radius: 6px;\n"
"    padding: 3px;\n"
"}\n"
"\n"
"QPushButton:hover {\n"
"    background-color: #444444;\n"
"}\n"
"\n"
"QPushButton:pressed {\n"
"    background-color: #2f2f2f;\n"
"}\n"
"")
        icon9 = QIcon()
        icon9.addFile(u"icons/algorithm.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.by_point.setIcon(icon9)
        self.by_point.setIconSize(QSize(24, 24))

        self.verticalLayout_7.addWidget(self.by_point)

        self.Rectangle = QPushButton(self.frame_5)
        self.Rectangle.setObjectName(u"Rectangle")
        self.Rectangle.setStyleSheet(u"QPushButton {\n"
"    background-color: #3c3c3c;\n"
"    border-top: 1px solid #4a4a4a;\n"
"    border-left: 1px solid #4a4a4a;\n"
"    border-right: 1px solid #4a4a4a;\n"
"    border-bottom: 1px solid #5b5b5b;\n"
"    border-radius: 6px;\n"
"    padding: 3px;\n"
"}\n"
"\n"
"QPushButton:hover {\n"
"    background-color: #444444;\n"
"}\n"
"\n"
"QPushButton:pressed {\n"
"    background-color: #2f2f2f;\n"
"}\n"
"")
        icon10 = QIcon()
        icon10.addFile(u"icons/rectangle-svgrepo-com.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.Rectangle.setIcon(icon10)
        self.Rectangle.setIconSize(QSize(24, 24))

        self.verticalLayout_7.addWidget(self.Rectangle)

        self.Join = QPushButton(self.frame_5)
        self.Join.setObjectName(u"Join")
        self.Join.setStyleSheet(u"QPushButton {\n"
"    background-color: #3c3c3c;\n"
"    border-top: 1px solid #4a4a4a;\n"
"    border-left: 1px solid #4a4a4a;\n"
"    border-right: 1px solid #4a4a4a;\n"
"    border-bottom: 1px solid #5b5b5b;\n"
"    border-radius: 6px;\n"
"    padding: 3px;\n"
"}\n"
"\n"
"QPushButton:hover {\n"
"    background-color: #444444;\n"
"}\n"
"\n"
"QPushButton:pressed {\n"
"    background-color: #2f2f2f;\n"
"}\n"
"\n"
"")
        icon11 = QIcon()
        icon11.addFile(u"icons/link-alt.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.Join.setIcon(icon11)
        self.Join.setIconSize(QSize(24, 24))

        self.verticalLayout_7.addWidget(self.Join)

        self.Cut = QPushButton(self.frame_5)
        self.Cut.setObjectName(u"Cut")
        self.Cut.setStyleSheet(u"QPushButton {\n"
"    background-color: #3c3c3c;\n"
"    border-top: 1px solid #4a4a4a;\n"
"    border-left: 1px solid #4a4a4a;\n"
"    border-right: 1px solid #4a4a4a;\n"
"    border-bottom: 1px solid #5b5b5b;\n"
"    border-radius: 6px;\n"
"    padding: 3px;\n"
"}\n"
"\n"
"QPushButton:hover {\n"
"    background-color: #444444;\n"
"}\n"
"\n"
"QPushButton:pressed {\n"
"    background-color: #2f2f2f;\n"
"}\n"
"\n"
"")
        icon12 = QIcon()
        icon12.addFile(u"icons/cut-svgrepo-com.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.Cut.setIcon(icon12)
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
        self.verticalLayout = QVBoxLayout(self.frame_4)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.horizontalLayout = QHBoxLayout()
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.horizontalSpacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout.addItem(self.horizontalSpacer)

        self.pushButton = QPushButton(self.frame_4)
        self.pushButton.setObjectName(u"pushButton")
        icon13 = QIcon()
        icon13.addFile(u"icons/cross.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.pushButton.setIcon(icon13)

        self.horizontalLayout.addWidget(self.pushButton)


        self.verticalLayout.addLayout(self.horizontalLayout)

        self.label = QLabel(self.frame_4)
        self.label.setObjectName(u"label")

        self.verticalLayout.addWidget(self.label)

        self.listWidget = QListWidget(self.frame_4)
        self.listWidget.setObjectName(u"listWidget")

        self.verticalLayout.addWidget(self.listWidget)

        self.verticalSpacer = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.verticalLayout.addItem(self.verticalSpacer)


        self.horizontalLayout_10.addWidget(self.frame_4)

        self.horizontalLayout_7 = QHBoxLayout()
        self.horizontalLayout_7.setObjectName(u"horizontalLayout_7")

        self.horizontalLayout_10.addLayout(self.horizontalLayout_7)


        self.gridLayout.addLayout(self.horizontalLayout_10, 0, 0, 1, 1)

        MainWindow.setCentralWidget(self.centralwidget)

        self.retranslateUi(MainWindow)

        QMetaObject.connectSlotsByName(MainWindow)
    # setupUi

    def retranslateUi(self, MainWindow):
        MainWindow.setWindowTitle(QCoreApplication.translate("MainWindow", u"MainWindow", None))
        self.import_button.setText(QCoreApplication.translate("MainWindow", u"import", None))
        self.import_sceen.setText(QCoreApplication.translate("MainWindow", u"import sceen", None))
        self.save_button.setText(QCoreApplication.translate("MainWindow", u"save", None))
        self.layers_batton.setText(QCoreApplication.translate("MainWindow", u"Layers panel", None))
        self.ai_panel.setText(QCoreApplication.translate("MainWindow", u"AI panel", None))
        self.settings.setText(QCoreApplication.translate("MainWindow", u"settings", None))
        self.cursor_Button.setText("")
        self.palette_Button.setText("")
        self.tools_Button.setText("")
        self.eye_Button.setText("")
        self.Resizable_button.setText("")
        self.label_7.setText(QCoreApplication.translate("MainWindow", u"object :", None))
        self.label_8.setText("")
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
        self.pushButton.setText("")
        self.label.setText(QCoreApplication.translate("MainWindow", u"Object list:", None))
    # retranslateUi

