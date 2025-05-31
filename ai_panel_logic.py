from PySide6.QtWidgets import (
    QMainWindow, QGraphicsScene, QGraphicsProxyWidget,
    QWidget, QGraphicsView, QVBoxLayout, QLabel, QFrame, QGraphicsItem, QSizePolicy, QScrollArea
)
from PySide6.QtGui import QPainter, QColor
from PySide6.QtCore import Qt, QPointF

from ui_ai_window import Ui_MainWindow as UiAIWindow

from ui_weather_tool import Ui_Form as UiWeatherTool
from ui_water_tool import Ui_Form as UiWaterTool
from ui_light_tool import Ui_Form as UiLightTool
from ui_fire_tool import Ui_Form as UiFireTool



class ShapeCard(QWidget):
    def __init__(self, shape_id, shape_type, color_name):
        super().__init__()
        self.shape_id = shape_id
        self.setFocusPolicy(Qt.NoFocus)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)

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
    def __init__(self, shape_id, parent_window):
        super().__init__()
        self.shape_id = shape_id
        self.parent_window = parent_window
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
            self.parent_window.ui.label_14.setText(str(self.shape_id))
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

        self.ui.weather_tool.clicked.connect(lambda: self.add_tool_panel(UiWeatherTool))
        self.ui.water_button.clicked.connect(lambda: self.add_tool_panel(UiWaterTool))
        self.ui.light_button.clicked.connect(lambda: self.add_tool_panel(UiLightTool))
        self.ui.fire_button.clicked.connect(lambda: self.add_tool_panel(UiFireTool))

        self.shape_cards = {}

        # Инициализируем layout внутри scrollArea
        self.tool_container_layout = QVBoxLayout(self.ui.scrollAreaWidgetContents)
        self.tool_container_layout.setSpacing(6)
        self.tool_container_layout.setContentsMargins(4, 4, 4, 4)

    def add_shape_card(self, shape_id, shape_type, color_name):
        shape_widget = ShapeCard(shape_id, shape_type, color_name)
        proxy = SelectableMovableProxy(shape_id, self)
        proxy.setWidget(shape_widget)
        proxy.setPos(40 + len(self.shape_cards) * 30, 40 + len(self.shape_cards) * 30)
        self.scene.addItem(proxy)
        self.shape_cards[shape_id] = proxy

    def add_tool_panel(self, ui_class):
        selected_id = self.ui.label_14.text().strip()

        # Если выбран ShapeCard
        if selected_id and selected_id in self.shape_cards:
            proxy = self.shape_cards[selected_id]
            shape_card = proxy.widget()

            # Если layout для инструментов ещё не создан — создаём
            if not hasattr(shape_card, "tool_layout"):
                shape_card.tool_layout = QVBoxLayout()
                shape_card.layout().addLayout(shape_card.tool_layout)

            # Удаляем уже добавленную панель этого типа
            for i in reversed(range(shape_card.tool_layout.count())):
                widget = shape_card.tool_layout.itemAt(i).widget()
                if widget and hasattr(widget, "_tool_class") and widget._tool_class == ui_class:
                    widget.setParent(None)

            # Создаём новую панель
            tool_widget = QWidget()
            ui = ui_class()
            ui.setupUi(tool_widget)
            tool_widget._tool_class = ui_class

            # Не растягивать
            size_policy = QSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
            tool_widget.setSizePolicy(size_policy)

            # Добавляем в выбранный ShapeCard
            shape_card.tool_layout.addWidget(tool_widget)
            return

        # Иначе — добавляем в scrollArea
        for i in reversed(range(self.tool_container_layout.count())):
            widget = self.tool_container_layout.itemAt(i).widget()
            if widget and hasattr(widget, "_tool_class") and widget._tool_class == ui_class:
                widget.setParent(None)

        tool_widget = QWidget()
        ui = ui_class()
        ui.setupUi(tool_widget)
        tool_widget._tool_class = ui_class

        size_policy = QSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        tool_widget.setSizePolicy(size_policy)

        self.tool_container_layout.addWidget(tool_widget)







