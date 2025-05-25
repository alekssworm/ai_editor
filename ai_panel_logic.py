from PySide6.QtWidgets import (
    QMainWindow, QGraphicsScene, QGraphicsProxyWidget,
    QWidget, QGraphicsView, QVBoxLayout, QLabel, QFrame, QGraphicsItem, QGraphicsRectItem
)
from PySide6.QtGui import QPainter, QColor
from PySide6.QtCore import Qt, QRectF

from ui_ai_window import Ui_MainWindow as UiAIWindow


class ShapeCardItem(QGraphicsRectItem):
    def __init__(self, shape_id, shape_type, color_name):
        super().__init__(0, 0, 120, 100)
        self.shape_id = shape_id
        self.shape_type = shape_type
        self.color_name = color_name

        self.setBrush(Qt.transparent)
        self.setPen(Qt.NoPen)

        self.setFlag(QGraphicsItem.ItemIsMovable, True)
        self.setFlag(QGraphicsItem.ItemIsSelectable, True)

        # Вложенный QWidget с лейблом и рамкой
        self.widget = QWidget()
        layout = QVBoxLayout(self.widget)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        # Лейбл
        self.label = QLabel(f"{shape_type} | ID: {shape_id}")
        self.label.setStyleSheet(f"""
            color: white;
            border: 2px solid {color_name};
            padding: 2px;
        """)
        layout.addWidget(self.label)

        # Рамка
        self.frame = QFrame()
        self.frame.setFixedSize(100, 60)
        self.frame.setStyleSheet(f"""
            background-color: transparent;
            border: 2px solid {color_name};
            border-radius: 4px;
        """)
        layout.addWidget(self.frame)

        self.widget.setLayout(layout)

        # Оборачиваем в прокси, чтобы вставить на сцену
        self.proxy = QGraphicsProxyWidget(self)
        self.proxy.setWidget(self.widget)
        self.proxy.setPos(0, 0)


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

        def default_mouse_press(event):
            QGraphicsScene.mousePressEvent(self.scene, event)

        def default_mouse_move(event):
            QGraphicsScene.mouseMoveEvent(self.scene, event)

        def default_mouse_release(event):
            QGraphicsScene.mouseReleaseEvent(self.scene, event)

        self.scene.mousePressEvent = default_mouse_press
        self.scene.mouseMoveEvent = default_mouse_move
        self.scene.mouseReleaseEvent = default_mouse_release

    def add_shape_card(self, shape_id, shape_type, color_name):
        shape_item = ShapeCardItem(shape_id, shape_type, color_name)
        shape_item.setPos(40 + len(self.shape_cards) * 30, 40 + len(self.shape_cards) * 30)
        self.scene.addItem(shape_item)

        self.shape_cards[shape_id] = shape_item
