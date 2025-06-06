from PySide6.QtWidgets import (
    QMainWindow, QGraphicsScene, QGraphicsProxyWidget,
    QWidget, QGraphicsView, QVBoxLayout, QLabel, QFrame, QGraphicsItem, QSizePolicy, QScrollArea, QPushButton,
    QComboBox, QHBoxLayout, QApplication
)
from PySide6.QtGui import QMouseEvent
from PySide6.QtGui import QPainter
from PySide6.QtCore import Qt, QPointF, QStringListModel

from ui_ai_window import Ui_MainWindow
from ui_weather_tool import Ui_weather_tool
from ui_water_tool import Ui_water_tool
from ui_light_tool import Ui_light_tool
from ui_fire_tool import Ui_fire_tool

from tool_Params import TOOL_PARAMETERS

from PySide6.QtWidgets import QComboBox, QListView


from PySide6.QtWidgets import QWidget, QVBoxLayout, QPushButton, QListView, QAbstractItemView

class InSceneComboBox(QWidget):
    def __init__(self, options=None, parent=None):
        super().__init__(parent)
        self.options = options or ["default", "low", "normal", "high"]
        self.button = QPushButton("select")
        self.view = QListView()
        self.view.setWindowFlags(Qt.Popup)
        self.view.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.view.setSelectionMode(QAbstractItemView.SingleSelection)

        self.model = QStringListModel(self.options)
        self.view.setModel(self.model)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.button)

        self.button.clicked.connect(self.show_popup)
        self.view.clicked.connect(self.select_option)

    def show_popup(self):
        self.view.setMinimumWidth(self.width())
        self.view.move(self.mapToGlobal(self.button.rect().bottomLeft()))
        self.view.show()

    def select_option(self, index):
        value = self.model.data(index)
        self.button.setText(value)
        self.view.hide()

    def setCurrentText(self, text):
        if text in self.options:
            self.button.setText(text)

    def addItems(self, items):
        self.options = items
        self.model.setStringList(items)



class ShapeCard(QWidget):
    def __init__(self, shape_id, shape_type, color_name):
        super().__init__()
        self.shape_id = shape_id
        self.setFocusPolicy(Qt.NoFocus)


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


from PySide6.QtWidgets import QGraphicsWidget, QGraphicsLinearLayout, QGraphicsProxyWidget
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QGraphicsItem

class ShapeCardGraphicsWidget(QGraphicsWidget):
    def __init__(self, shape_id, shape_widget, parent_window):
        super().__init__()
        self.shape_id = shape_id
        self.parent_window = parent_window

        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
        self.setAcceptedMouseButtons(Qt.LeftButton)

        layout = QGraphicsLinearLayout(Qt.Vertical)
        proxy = QGraphicsProxyWidget(self)
        proxy.setWidget(shape_widget)
        layout.addItem(proxy)

        self.setLayout(layout)

    def mousePressEvent(self, event):
        self.setSelected(True)
        if self.parent_window and hasattr(self.parent_window.ui, "label_14"):
            self.parent_window.ui.label_14.setText(str(self.shape_id))
        super().mousePressEvent(event)


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
        widget = ShapeCardGraphicsWidget(shape_id, shape_widget, self)
        widget.setPos(40 + len(self.shape_cards) * 30, 40 + len(self.shape_cards) * 30)
        self.scene.addItem(widget)
        self.shape_cards[shape_id] = widget

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

        proxy = self.shape_cards[selected_id].layout().itemAt(0)
        shape_card = proxy.widget() if proxy else None

        if not shape_card:
            print(f"[DEBUG] ❌ Не удалось получить ShapeCard для ID {selected_id}")
            return

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

        # Добавление параметров
        param_block = QVBoxLayout()
        label = QLabel(button_text)
        label.setStyleSheet("color: white; font-weight: bold;")
        param_block.addWidget(label)

        params = TOOL_PARAMETERS.get(button_name, [])
        for param in params:
            row = QHBoxLayout()
            row.setSpacing(6)
            label = QLabel(param)
            combo = InSceneComboBox()
            combo.addItems(["none", "default", "weak", "normal", "strong"])
            combo.setCurrentText("default")
            combo.setFocusPolicy(Qt.StrongFocus)
            combo.setFocus()
            combo.setStyleSheet("background-color: #2a2a2a; color: white; padding: 2px;")

            label.setStyleSheet("color: lightgray")


            row.addWidget(label)
            row.addWidget(combo)

            param_block.addLayout(row)

        wrapper = QWidget()
        wrapper.setLayout(param_block)
        wrapper.setStyleSheet("background-color: rgba(255, 255, 255, 0.05); border-radius: 6px; padding: 4px;")

        shape_card.frame_layout.addWidget(wrapper)

