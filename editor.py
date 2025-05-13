import sys

from PySide6.QtGui import QPixmap, QWheelEvent, QColor
from PySide6.QtWidgets import QApplication, QMainWindow, QGraphicsScene, QFileDialog, QGraphicsPixmapItem, QGraphicsView
from ui_editor import Ui_MainWindow  # Это ваш сгенерированный класс
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QFileDialog, QGraphicsScene, QGraphicsPixmapItem
from PySide6.QtCore import Qt, QEvent
from PySide6.QtWidgets import QLabel

from import_image import import_image
from zoom import GraphicsViewWithZoom
from colors_menu import choose_color
from hide_or_unhide_panels import toggle_tools_panel,toggle_layers_panel

from draw_logic import DrawingToolController

from Activate_disconect_button import activate_rectangle_mode ,deactivate_drawing_mode,activate_circle_mode
from on_shape_selected import on_shape_selected
from save_logic import save_outputs
from show_all_handle import show_all_handles

from m_event import MouseMoveFilter


from navigation_overlay import NavigationOverlay






class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)




        #--------
        self.graphics_view = GraphicsViewWithZoom(self)
        # Удаляем старый виджет из layout (без удаления объекта)
        self.ui.horizontalLayout_9.removeWidget(self.ui.graphicsView)
        # Добавляем новый
        self.ui.horizontalLayout_9.addWidget(self.graphics_view)
        # При желании — скрыть старый
        self.ui.graphicsView.hide()
        # Присвоить новый виджет на место старого, если ты его используешь дальше
        self.ui.graphicsView = self.graphics_view

        # Сцена и подключение
        self.scene = QGraphicsScene()
        self.ui.graphicsView.setScene(self.scene)
        #----------

        # Спрятать панели при старте
        self.ui.frame_5.hide()  # Левая панель в verticalLayout_6
        self.ui.frame_4.hide()  # Правая панель в horizontalLayout_7

        # Obj id
        self.shape_registry = {}  # {id: QGraphicsItem}
        self.shape_id_counter = 1


        # Подключение логики переключения
        self.ui.tools_Button.clicked.connect(lambda:toggle_tools_panel(self))
        self.ui.layers_batton.clicked.connect(lambda:toggle_layers_panel(self))

        self.scene.selectionChanged.connect(lambda :on_shape_selected(self))

        # Подключение кнопки "import"
        self.ui.import_button.clicked.connect(lambda: import_image(self))

        # Подключение кнопки "palette_Button"
        self.ui.palette_Button.clicked.connect(lambda:choose_color(self))


        # Создаём контроллер, но не активируем сразу
        self.current_shape_color = QColor(255, 0, 0, 50)  # Цвет по умолчанию
        self.draw_controller = DrawingToolController(self.scene, self)

        # Подключаем кнопки инструментов
        self.ui.Rectangle.clicked.connect(lambda:activate_rectangle_mode(self))
        self.ui.Cursor.clicked.connect(lambda:deactivate_drawing_mode(self))
        self.ui.cursor_Button.clicked.connect(lambda:deactivate_drawing_mode(self))

        self.ui.Circle.clicked.connect(lambda:activate_circle_mode(self))

        self.ui.save_button.clicked.connect(lambda:save_outputs(self))

        self.ui.Resizable_button.clicked.connect(lambda:show_all_handles(self))

        self.navigation_overlay = NavigationOverlay(self.ui.graphicsView, self)

        # Подключаем фильтр движения мыши
        self.mouse_filter = MouseMoveFilter(self.navigation_overlay, self.scene)
        self.scene.installEventFilter(self.mouse_filter)




if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
