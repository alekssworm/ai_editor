import sys

from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QGraphicsScene, QGraphicsPixmapItem
)
from ui_editor import Ui_MainWindow

from import_image import import_image
from zoom import GraphicsViewWithZoom
from colors_menu import choose_color
from hide_or_unhide_panels import toggle_tools_panel, toggle_layers_panel

from draw_logic import DrawingToolController
from Activate_disconect_button import (
    activate_rectangle_mode, deactivate_drawing_mode, activate_circle_mode
)
from on_shape_selected import on_shape_selected
from save_logic import save_outputs
from show_all_handle import show_all_handles

from navigation_overlay import NavigationOverlay
from m_event import MouseMoveFilter
from obj_list_logic import add_shape_to_list



class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)

        # Заменяем стандартный graphicsView на улучшенный
        self.graphics_view = GraphicsViewWithZoom(self)
        self.ui.horizontalLayout_9.removeWidget(self.ui.graphicsView)
        self.ui.horizontalLayout_9.addWidget(self.graphics_view)
        self.ui.graphicsView.hide()
        self.ui.graphicsView = self.graphics_view

        # Создаём сцену и устанавливаем в graphicsView
        self.scene = QGraphicsScene()
        self.ui.graphicsView.setScene(self.scene)

        # Панели скрыты при старте
        self.ui.frame_5.hide()
        self.ui.frame_4.hide()

        # Регистрация фигур
        self.shape_registry = {}  # {id: QGraphicsItem}
        self.shape_id_counter = 1

        # Кнопки UI
        self.ui.tools_Button.clicked.connect(lambda: toggle_tools_panel(self))
        self.ui.layers_batton.clicked.connect(lambda: toggle_layers_panel(self))
        self.ui.import_button.clicked.connect(lambda: import_image(self))
        self.ui.palette_Button.clicked.connect(lambda: choose_color(self))
        self.ui.Rectangle.clicked.connect(lambda: activate_rectangle_mode(self))
        self.ui.Cursor.clicked.connect(lambda: deactivate_drawing_mode(self))
        self.ui.cursor_Button.clicked.connect(lambda: deactivate_drawing_mode(self))
        self.ui.Circle.clicked.connect(lambda: activate_circle_mode(self))
        self.ui.save_button.clicked.connect(lambda: save_outputs(self))
        self.ui.Resizable_button.clicked.connect(lambda: show_all_handles(self))

        # Подключение селектора
        self.scene.selectionChanged.connect(lambda: on_shape_selected(self))

        # Настройки рисования
        self.current_shape_color = QColor(255, 0, 0, 50)
        self.draw_controller = DrawingToolController(self.scene, self)

        # 🧠 Важно: добавляем overlay после сцены
        self.navigation_overlay = NavigationOverlay(self.ui.graphicsView, self)

        # 🐭 Установка фильтра мыши на сцену
        self.mouse_filter = MouseMoveFilter(self.navigation_overlay, self.scene)
        self.scene.installEventFilter(self.mouse_filter)




if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
