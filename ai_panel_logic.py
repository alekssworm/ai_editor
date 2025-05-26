from PySide6.QtWidgets import (
    QMainWindow, QGraphicsScene, QGraphicsProxyWidget,
    QWidget, QGraphicsView, QVBoxLayout, QLabel, QFrame, QGraphicsItem
)
from PySide6.QtGui import QPainter, QColor
from PySide6.QtCore import Qt, QPointF

from ui_ai_window import Ui_MainWindow as UiAIWindow


class ShapeCard(QWidget):
    def __init__(self, shape_id, shape_type, color_name):
        super().__init__()
        self.setFocusPolicy(Qt.NoFocus)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)  # ключевой момент

        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        label = QLabel(f"{shape_type} | ID: {shape_id}")
        label.setStyleSheet(f"""
            color: white;
            border: 2px solid {color_name};
            padding: 2px;
        """)
        label.setFocusPolicy(Qt.NoFocus)
        layout.addWidget(label)

        frame = QFrame()
        frame.setFixedSize(100, 60)
        frame.setStyleSheet(f"""
            background-color: transparent;
            border: 2px solid {color_name};
            border-radius: 4px;
        """)
        layout.addWidget(frame)


class SelectableMovableProxy(QGraphicsProxyWidget):
    def __init__(self):
        super().__init__()
        self.setAcceptedMouseButtons(Qt.LeftButton)
        self.setAcceptHoverEvents(True)
        self.setFlag(QGraphicsItem.ItemIsMovable, True)
        self.setFlag(QGraphicsItem.ItemIsSelectable, True)
        self._drag_offset = QPointF()
        self._dragging = False

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_offset = event.pos()
            self.setCursor(Qt.ClosedHandCursor)
            self.setSelected(True)
            self._dragging = True
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._dragging:
            new_pos = self.pos() + (event.pos() - self._drag_offset)
            self.setPos(new_pos)
            event.accept()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self._dragging:
            self.setCursor(Qt.ArrowCursor)
            self._dragging = False
            event.accept()
        else:
            super().mouseReleaseEvent(event)


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

    def add_shape_card(self, shape_id, shape_type, color_name):
        shape_widget = ShapeCard(shape_id, shape_type, color_name)
        proxy = SelectableMovableProxy()
        proxy.setWidget(shape_widget)
        proxy.setPos(40 + len(self.shape_cards) * 30, 40 + len(self.shape_cards) * 30)
        self.scene.addItem(proxy)
        self.shape_cards[shape_id] = proxy
