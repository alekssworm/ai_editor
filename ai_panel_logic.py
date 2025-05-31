from PySide6.QtWidgets import (
    QMainWindow, QGraphicsScene, QGraphicsProxyWidget,
    QWidget, QGraphicsView, QVBoxLayout, QLabel, QFrame, QGraphicsItem, QSizePolicy, QScrollArea, QPushButton
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

        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(4, 4, 4, 4)
        self.main_layout.setSpacing(4)

        label = QLabel(f"{shape_type} | ID: {shape_id}")
        label.setStyleSheet(f"""
            color: white;
            border: 2px solid {color_name};
            padding: 2px;
        """)
        label.setFocusPolicy(Qt.NoFocus)
        self.main_layout.addWidget(label)

        # 🔁 Рамка-контейнер
        self.frame = QFrame()
        self.frame.setStyleSheet(f"""
            background-color: transparent;
            border: 2px solid {color_name};
            border-radius: 4px;
        """)
        self.main_layout.addWidget(self.frame)

        # ⬇ Внутри рамки — вертикальный layout
        self.frame_layout = QVBoxLayout(self.frame)
        self.frame_layout.setContentsMargins(4, 4, 4, 4)
        self.frame_layout.setSpacing(4)



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
            print(f"[DEBUG] ShapeCard selected: ID = {self.shape_id}")
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
        print(f"[DEBUG] ShapeCard created: ID = {shape_id}")

    def add_button_name_to_shape_card(self, button_text):
        print(f"[DEBUG] Нажата кнопка: {button_text}")
        try:
            selected_id = int(self.ui.label_14.text().strip())
            print(f"[DEBUG] ShapeCard ID из label_14: {selected_id}")
        except ValueError:
            print("[DEBUG] label_14 пустой или некорректный")
            return

        if selected_id not in self.shape_cards:
            print(f"[DEBUG] ShapeCard с ID {selected_id} не найден")
            return

        shape_card = self.shape_cards[selected_id].widget()

        label = QLabel(button_text)
        label.setStyleSheet("color: white; background: rgba(255, 255, 255, 0.1); padding: 2px 4px; border-radius: 4px;")
        shape_card.frame_layout.addWidget(label)
        print(f"[DEBUG] Добавлен элемент '{button_text}' в ShapeCard ID {selected_id}")

    def add_tool_panel(self, ui_class):
        tool_widget = QWidget()
        ui = ui_class()
        ui.setupUi(tool_widget)

        buttons = tool_widget.findChildren(QPushButton)
        print(f"[DEBUG] Найдено {len(buttons)} кнопок в {ui_class.__name__}")

        for btn in buttons:
            btn_text = btn.text().strip()
            if btn_text and btn_text.lower() not in ["x", "color"]:
                btn.clicked.connect(lambda _, text=btn_text: self.add_button_name_to_shape_card(text))
                print(f"[DEBUG] Привязан обработчик к кнопке: {btn_text}")

        # Удалить старую панель
        for i in reversed(range(self.tool_container_layout.count())):
            widget = self.tool_container_layout.itemAt(i).widget()
            if widget and hasattr(widget, "_tool_class") and widget._tool_class == ui_class:
                widget.setParent(None)

        tool_widget._tool_class = ui_class
        size_policy = QSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        tool_widget.setSizePolicy(size_policy)
        self.tool_container_layout.addWidget(tool_widget)
