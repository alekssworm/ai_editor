# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'ai_window.ui'
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
from PySide6.QtWidgets import (QApplication, QFrame, QGraphicsView, QGridLayout,
    QHBoxLayout, QLabel, QLayout, QMainWindow,
    QPushButton, QScrollArea, QSizePolicy, QSpacerItem,
    QVBoxLayout, QWidget)

class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        if not MainWindow.objectName():
            MainWindow.setObjectName(u"MainWindow")
        MainWindow.resize(1743, 1116)
        self.centralwidget = QWidget(MainWindow)
        self.centralwidget.setObjectName(u"centralwidget")
        self.gridLayout_5 = QGridLayout(self.centralwidget)
        self.gridLayout_5.setObjectName(u"gridLayout_5")
        self.gridLayout_4 = QGridLayout()
        self.gridLayout_4.setObjectName(u"gridLayout_4")
        self.gridLayout_2 = QGridLayout()
        self.gridLayout_2.setObjectName(u"gridLayout_2")
        self.gridLayout = QGridLayout()
        self.gridLayout.setObjectName(u"gridLayout")
        self.gridLayout.setSizeConstraint(QLayout.SizeConstraint.SetMaximumSize)
        self.graphicsView = QGraphicsView(self.centralwidget)
        self.graphicsView.setObjectName(u"graphicsView")

        self.gridLayout.addWidget(self.graphicsView, 0, 0, 1, 1)


        self.gridLayout_2.addLayout(self.gridLayout, 1, 0, 1, 1)

        self.horizontalLayout_2 = QHBoxLayout()
        self.horizontalLayout_2.setObjectName(u"horizontalLayout_2")
        self.frame_2 = QFrame(self.centralwidget)
        self.frame_2.setObjectName(u"frame_2")
        self.frame_2.setFrameShape(QFrame.Shape.StyledPanel)
        self.frame_2.setFrameShadow(QFrame.Shadow.Raised)
        self.gridLayout_3 = QGridLayout(self.frame_2)
        self.gridLayout_3.setObjectName(u"gridLayout_3")
        self.horizontalLayout_3 = QHBoxLayout()
        self.horizontalLayout_3.setObjectName(u"horizontalLayout_3")
        self.pushButton_9 = QPushButton(self.frame_2)
        self.pushButton_9.setObjectName(u"pushButton_9")

        self.horizontalLayout_3.addWidget(self.pushButton_9)

        self.water_button = QPushButton(self.frame_2)
        self.water_button.setObjectName(u"water_button")

        self.horizontalLayout_3.addWidget(self.water_button)

        self.fire_button = QPushButton(self.frame_2)
        self.fire_button.setObjectName(u"fire_button")

        self.horizontalLayout_3.addWidget(self.fire_button)

        self.light_button = QPushButton(self.frame_2)
        self.light_button.setObjectName(u"light_button")

        self.horizontalLayout_3.addWidget(self.light_button)

        self.weather_tool = QPushButton(self.frame_2)
        self.weather_tool.setObjectName(u"weather_tool")

        self.horizontalLayout_3.addWidget(self.weather_tool)

        self.label_13 = QLabel(self.frame_2)
        self.label_13.setObjectName(u"label_13")

        self.horizontalLayout_3.addWidget(self.label_13)

        self.label_14 = QLabel(self.frame_2)
        self.label_14.setObjectName(u"label_14")
        self.label_14.setMinimumSize(QSize(100, 0))

        self.horizontalLayout_3.addWidget(self.label_14)

        self.horizontalSpacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_3.addItem(self.horizontalSpacer)


        self.gridLayout_3.addLayout(self.horizontalLayout_3, 0, 0, 1, 1)


        self.horizontalLayout_2.addWidget(self.frame_2)


        self.gridLayout_2.addLayout(self.horizontalLayout_2, 0, 0, 1, 1)


        self.gridLayout_4.addLayout(self.gridLayout_2, 0, 0, 1, 1)

        self.verticalLayout = QVBoxLayout()
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.verticalLayout.setSizeConstraint(QLayout.SizeConstraint.SetFixedSize)
        self.frame = QFrame(self.centralwidget)
        self.frame.setObjectName(u"frame")
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Maximum)
        sizePolicy.setHorizontalStretch(30)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.frame.sizePolicy().hasHeightForWidth())
        self.frame.setSizePolicy(sizePolicy)
        self.frame.setMinimumSize(QSize(300, 0))
        self.frame.setMaximumSize(QSize(300, 50000))
        self.frame.setFrameShape(QFrame.Shape.StyledPanel)
        self.frame.setFrameShadow(QFrame.Shadow.Raised)
        self._2 = QHBoxLayout(self.frame)
        self._2.setObjectName(u"_2")
        self.scrollArea = QScrollArea(self.frame)
        self.scrollArea.setObjectName(u"scrollArea")
        self.scrollArea.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scrollArea.setWidgetResizable(True)
        self.scrollAreaWidgetContents = QWidget()
        self.scrollAreaWidgetContents.setObjectName(u"scrollAreaWidgetContents")
        self.scrollAreaWidgetContents.setGeometry(QRect(0, 0, 278, 1072))
        self.scrollArea.setWidget(self.scrollAreaWidgetContents)

        self._2.addWidget(self.scrollArea)


        self.verticalLayout.addWidget(self.frame)


        self.gridLayout_4.addLayout(self.verticalLayout, 0, 1, 1, 1)


        self.gridLayout_5.addLayout(self.gridLayout_4, 0, 0, 1, 1)

        MainWindow.setCentralWidget(self.centralwidget)

        self.retranslateUi(MainWindow)

        QMetaObject.connectSlotsByName(MainWindow)
    # setupUi

    def retranslateUi(self, MainWindow):
        MainWindow.setWindowTitle(QCoreApplication.translate("MainWindow", u"MainWindow", None))
        self.pushButton_9.setText(QCoreApplication.translate("MainWindow", u"save", None))
        self.water_button.setText(QCoreApplication.translate("MainWindow", u"water tool", None))
        self.fire_button.setText(QCoreApplication.translate("MainWindow", u"fire tool", None))
        self.light_button.setText(QCoreApplication.translate("MainWindow", u"light tool", None))
        self.weather_tool.setText(QCoreApplication.translate("MainWindow", u"weather tool", None))
        self.label_13.setText(QCoreApplication.translate("MainWindow", u"object:", None))
        self.label_14.setText("")
    # retranslateUi

