from PySide6.QtWidgets import (
    QMainWindow, QGraphicsScene, QGraphicsProxyWidget,
    QWidget, QGraphicsView, QVBoxLayout, QLabel, QFrame, QPushButton, QGraphicsItem
)
from PySide6.QtGui import QPainter, QColor, QDrag, QPixmap
from PySide6.QtCore import Qt, QMimeData, QPoint

from ui_ai_window import Ui_MainWindow as UiAIWindow


class DraggableButton(QPushButton):
    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton:
            drag = QDrag(self)
            mime = QMimeData()
            mime.setText(self.text())
            drag.setMimeData(mime)
            drag.setHotSpot(event.pos())
            drag.setPixmap(self.grab())
            print("🚀 Drag started with:", self.text())
            drag.exec(Qt.CopyAction)
        else:
            super().mouseMoveEvent(event)


class DropFrame(QFrame):
    def __init__(self, border_color):
        super().__init__()
        self.setAcceptDrops(True)
        self.setFixedSize(100, 60)
        self.setStyleSheet(f"""
            background-color: transparent;
            border: 2px solid {border_color};
            border-radius: 4px;
        """)

        self.layout = QVBoxLayout(self)
        self.label = QLabel("Drop tool here")
        self.label.setAlignment(Qt.AlignCenter)
        self.label.setStyleSheet("color: white;")
        self.layout.addWidget(self.label)

    def dragEnterEvent(self, event):
        if event.mimeData().hasText():
            print("🚀 drag enter")
            event.acceptProposedAction()

    def dropEvent(self, event):
        if event.mimeData().hasText():
            tool_name = event.mimeData().text()
            print("✅ dropped:", tool_name)
            self.label.setText(tool_name)
            event.acceptProposedAction()
        else:
            print("⚠️ dropEvent ignored")


class ShapeCard(QWidget):
    def __init__(self, shape_id, shape_type, color_name):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        label = QLabel(f"{shape_type} | ID: {shape_id}")
        label.setStyleSheet(f"""
            color: white;
            border: 2px solid {color_name};
            padding: 2px;
        """)
        layout.addWidget(label)

        self.frame = DropFrame(color_name)
        layout.addWidget(self.frame)


class AIWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.ui = UiAIWindow()
        self.ui.setupUi(self)

        self.scene = QGraphicsScene(self)
        self.ui.graphicsView.setRenderHint(QPainter.Antialiasing)
        self.ui.graphicsView.setScene(self.scene)
        self.ui.graphicsView.setDragMode(QGraphicsView.NoDrag)
        self.ui.graphicsView.setStyleSheet("background-color: #1e1e1e; border: none;")
        self.ui.graphicsView.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.ui.graphicsView.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        self.shape_cards = {}

        tool_buttons = [
            self.ui.pushButton_13, self.ui.pushButton_14, self.ui.pushButton_15,
            self.ui.pushButton_16, self.ui.pushButton_17, self.ui.pushButton_18,
            self.ui.pushButton_19, self.ui.pushButton_20, self.ui.pushButton_21,
            self.ui.pushButton_22, self.ui.pushButton_23, self.ui.pushButton_24,
            self.ui.pushButton_25, self.ui.pushButton_26, self.ui.pushButton_27,
            self.ui.pushButton_28, self.ui.pushButton_29, self.ui.pushButton_30,
            self.ui.pushButton_40, self.ui.pushButton_41, self.ui.pushButton_42,
            self.ui.pushButton_43, self.ui.pushButton_44, self.ui.pushButton_45,
            self.ui.pushButton_46, self.ui.pushButton_47, self.ui.pushButton_48,
            self.ui.pushButton_49, self.ui.pushButton_50, self.ui.pushButton_51,
            self.ui.pushButton_52, self.ui.pushButton_53, self.ui.pushButton_54,
            self.ui.pushButton_55, self.ui.pushButton_56, self.ui.pushButton_57
        ]

        for i, btn in enumerate(tool_buttons):
            parent = btn.parent()
            new_btn = DraggableButton(btn.text(), parent)
            new_btn.setGeometry(btn.geometry())
            new_btn.setStyleSheet(btn.styleSheet())
            btn.hide()

    def add_shape_card(self, shape_id, shape_type, color_name):
        shape_widget = ShapeCard(shape_id, shape_type, color_name)
        proxy = QGraphicsProxyWidget()
        proxy.setWidget(shape_widget)
        proxy.setPos(40 + len(self.shape_cards) * 30, 40 + len(self.shape_cards) * 30)
        proxy.setFlag(QGraphicsItem.ItemIsMovable, True)
        proxy.setFlag(QGraphicsItem.ItemIsSelectable, True)
        self.scene.addItem(proxy)
        self.shape_cards[shape_id] = proxy