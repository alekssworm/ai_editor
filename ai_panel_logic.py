from PySide6.QtWidgets import (
    QMainWindow, QGraphicsScene, QGraphicsProxyWidget,
    QWidget, QGraphicsView, QVBoxLayout, QLabel, QFrame, QGraphicsItem, QSizePolicy, QScrollArea, QPushButton
)
from PySide6.QtGui import QPainter
from PySide6.QtCore import Qt, QPointF

from ui_ai_window import Ui_MainWindow
from ui_weather_tool import Ui_weather_tool
from ui_water_tool import Ui_water_tool
from ui_light_tool import Ui_light_tool
from ui_fire_tool import Ui_fire_tool


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

        self.frame = QFrame()
        self.frame.setStyleSheet(f"""
            background-color: transparent;
            border: 2px solid {color_name};
            border-radius: 4px;
        """)
        self.main_layout.addWidget(self.frame)

        self.frame_layout = QVBoxLayout(self.frame)
        self.frame_layout.setContentsMargins(4, 4, 4, 4)
        self.frame_layout.setSpacing(4)

        self.tool_type = None
        self.main_function_added = False
        self.added_subfunctions = set()


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
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)

        self.scene = QGraphicsScene(self)
        self.ui.graphicsView.setRenderHint(QPainter.Antialiasing)
        self.ui.graphicsView.setScene(self.scene)
        self.ui.graphicsView.setDragMode(QGraphicsView.NoDrag)
        self.ui.graphicsView.setStyleSheet("background-color: #1e1e1e; border: none;")
        self.ui.graphicsView.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.ui.graphicsView.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        self.ui.weather_tool.clicked.connect(lambda: self.load_tool_panel(Ui_weather_tool))
        self.ui.water_button.clicked.connect(lambda: self.load_tool_panel(Ui_water_tool))
        self.ui.light_button.clicked.connect(lambda: self.load_tool_panel(Ui_light_tool))
        self.ui.fire_button.clicked.connect(lambda: self.load_tool_panel(Ui_fire_tool))

        self.shape_cards = {}
        self.last_tool_type = None

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

    def load_tool_panel(self, ui_class):
        self.last_tool_type = ui_class.__name__
        print(f"[DEBUG] 🔄 Активирован инструмент: {self.last_tool_type}")

        tool_widget = QWidget()
        ui = ui_class()
        ui.setupUi(tool_widget)

        buttons = tool_widget.findChildren(QPushButton)
        print(f"[DEBUG] Найдено {len(buttons)} кнопок в {ui_class.__name__}")

        for btn in buttons:
            btn_text = btn.text().strip()
            btn_name = btn.objectName().strip()
            if btn_text and btn_name.lower() not in ["x", "color"]:
                btn.clicked.connect(lambda _, text=btn_text, name=btn_name: self.add_button_name_to_shape_card(text, name))
                print(f"[DEBUG] Привязан обработчик к кнопке: {btn_text} ({btn_name})")

        tool_widget._tool_class = ui_class
        size_policy = QSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        tool_widget.setSizePolicy(size_policy)
        self.tool_container_layout.addWidget(tool_widget)

    def add_button_name_to_shape_card(self, button_text, button_name):
        print(f"[DEBUG] Нажата кнопка: {button_text} ({button_name})")
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

        tool_type = self.last_tool_type.lower().replace('ui_', '').replace('_tool', '')
        is_main = button_name.lower().startswith('main_')
        is_sub = button_name.lower().startswith('sub_')

        if shape_card.tool_type and shape_card.tool_type != tool_type:
            print(f"[DEBUG] ❌ Нельзя смешивать инструменты: {shape_card.tool_type} != {tool_type}")
            return

        if not shape_card.tool_type:
            shape_card.tool_type = tool_type
            print(f"[DEBUG] ✅ Назначен tool_type: {tool_type}")

        if is_main:
            if shape_card.main_function_added:
                print(f"[DEBUG] ⚠ Главная функция уже добавлена в ShapeCard {selected_id}")
                return
            shape_card.main_function_added = True
            print(f"[DEBUG] ✅ Добавлена главная функция: {button_text}")
        elif is_sub:
            if button_name in shape_card.added_subfunctions:
                print(f"[DEBUG] ⚠ Саб-функция уже добавлена: {button_text} ({button_name})")
                return
            shape_card.added_subfunctions.add(button_name)
            print(f"[DEBUG] ➕ Добавлена саб-функция: {button_text}")
        else:
            print(f"[DEBUG] ❗ Неизвестный тип кнопки: {button_text} ({button_name})")
            return

        label = QLabel(button_text)
        label.setStyleSheet("color: white; background: rgba(255,255,255,0.1); padding: 2px 4px; border-radius: 4px;")
        shape_card.frame_layout.addWidget(label)