# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'tools_panel.ui'
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
from PySide6.QtWidgets import (QApplication, QFrame, QHBoxLayout, QPushButton,
    QSizePolicy, QVBoxLayout, QWidget)

class Ui_Form(object):
    def setupUi(self, Form):
        if not Form.objectName():
            Form.setObjectName(u"Form")
        Form.resize(297, 228)
        self.horizontalLayout_3 = QHBoxLayout(Form)
        self.horizontalLayout_3.setObjectName(u"horizontalLayout_3")
        self.frame = QFrame(Form)
        self.frame.setObjectName(u"frame")
        self.frame.setFrameShape(QFrame.Shape.StyledPanel)
        self.frame.setFrameShadow(QFrame.Shadow.Raised)
        self.horizontalLayout_7 = QHBoxLayout(self.frame)
        self.horizontalLayout_7.setObjectName(u"horizontalLayout_7")
        self.verticalLayout = QVBoxLayout()
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.horizontalLayout = QHBoxLayout()
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.Cursor = QPushButton(self.frame)
        self.Cursor.setObjectName(u"Cursor")

        self.horizontalLayout.addWidget(self.Cursor)

        self.Freeform = QPushButton(self.frame)
        self.Freeform.setObjectName(u"Freeform")

        self.horizontalLayout.addWidget(self.Freeform)


        self.verticalLayout.addLayout(self.horizontalLayout)

        self.horizontalLayout_2 = QHBoxLayout()
        self.horizontalLayout_2.setObjectName(u"horizontalLayout_2")
        self.Semicircle = QPushButton(self.frame)
        self.Semicircle.setObjectName(u"Semicircle")

        self.horizontalLayout_2.addWidget(self.Semicircle)

        self.Rounding = QPushButton(self.frame)
        self.Rounding.setObjectName(u"Rounding")

        self.horizontalLayout_2.addWidget(self.Rounding)


        self.verticalLayout.addLayout(self.horizontalLayout_2)

        self.horizontalLayout_4 = QHBoxLayout()
        self.horizontalLayout_4.setObjectName(u"horizontalLayout_4")
        self.Join = QPushButton(self.frame)
        self.Join.setObjectName(u"Join")

        self.horizontalLayout_4.addWidget(self.Join)

        self.Cut = QPushButton(self.frame)
        self.Cut.setObjectName(u"Cut")

        self.horizontalLayout_4.addWidget(self.Cut)


        self.verticalLayout.addLayout(self.horizontalLayout_4)

        self.horizontalLayout_5 = QHBoxLayout()
        self.horizontalLayout_5.setObjectName(u"horizontalLayout_5")
        self.Circle = QPushButton(self.frame)
        self.Circle.setObjectName(u"Circle")

        self.horizontalLayout_5.addWidget(self.Circle)

        self.Rectangle = QPushButton(self.frame)
        self.Rectangle.setObjectName(u"Rectangle")

        self.horizontalLayout_5.addWidget(self.Rectangle)


        self.verticalLayout.addLayout(self.horizontalLayout_5)

        self.horizontalLayout_6 = QHBoxLayout()
        self.horizontalLayout_6.setObjectName(u"horizontalLayout_6")
        self.Angle = QPushButton(self.frame)
        self.Angle.setObjectName(u"Angle")

        self.horizontalLayout_6.addWidget(self.Angle)

        self.pushButton_2 = QPushButton(self.frame)
        self.pushButton_2.setObjectName(u"pushButton_2")

        self.horizontalLayout_6.addWidget(self.pushButton_2)


        self.verticalLayout.addLayout(self.horizontalLayout_6)


        self.horizontalLayout_7.addLayout(self.verticalLayout)


        self.horizontalLayout_3.addWidget(self.frame)


        self.retranslateUi(Form)

        QMetaObject.connectSlotsByName(Form)
    # setupUi

    def retranslateUi(self, Form):
        Form.setWindowTitle(QCoreApplication.translate("Form", u"Form", None))
        self.Cursor.setText(QCoreApplication.translate("Form", u"Cursor", None))
        self.Freeform.setText(QCoreApplication.translate("Form", u"Freeform", None))
        self.Semicircle.setText(QCoreApplication.translate("Form", u"Semicircle", None))
        self.Rounding.setText(QCoreApplication.translate("Form", u"Rounding", None))
        self.Join.setText(QCoreApplication.translate("Form", u"Join", None))
        self.Cut.setText(QCoreApplication.translate("Form", u"Cut", None))
        self.Circle.setText(QCoreApplication.translate("Form", u"Circle", None))
        self.Rectangle.setText(QCoreApplication.translate("Form", u"Rectangle", None))
        self.Angle.setText(QCoreApplication.translate("Form", u"Angle", None))
        self.pushButton_2.setText(QCoreApplication.translate("Form", u"By Points", None))
    # retranslateUi

