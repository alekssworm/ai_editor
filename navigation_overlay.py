from PySide6.QtWidgets import QWidget
from PySide6.QtCore import QEvent, QObject, Qt
from ui_navigation import Ui_Form

class NavigationOverlay(QObject):
    def __init__(self, parent_view, main_window):
        super().__init__()
        self.parent_view = parent_view
        self.main_window = main_window  # Получаем доступ к shape_registry

        self.widget = QWidget(parent_view)
        self.ui = Ui_Form()
        self.ui.setupUi(self.widget)

        self.widget.setAttribute(Qt.WA_TranslucentBackground)
        self.widget.setAttribute(Qt.WA_TransparentForMouseEvents, False)
        self.widget.setWindowFlags(Qt.FramelessWindowHint)

        self.widget.setStyleSheet("background-color: rgba(0, 0, 0, 160); border-radius: 6px;")
        self.ui.label.setStyleSheet("color: white; background: transparent;")
        self.widget.setFixedSize(200, 60)

        self.widget.show()
        self.reposition()

        parent_view.viewport().installEventFilter(self)
        self.parent_view.installEventFilter(self)

    def reposition(self):
        view_size = self.parent_view.viewport().size()
        x = 10  # отступ слева
        y = view_size.height() - self.widget.height() - 10  # отступ снизу
        self.widget.move(x, y)
        self.widget.raise_()

    def eventFilter(self, source, event):
        if event.type() == QEvent.GraphicsSceneMouseMove:
            scene_pos = event.scenePos()

            hovered_id = "0"
            hovered_color = "transparent"

            for shape_id, item in self.main_window.shape_registry.items():
                rect = item.sceneBoundingRect()
                if rect.contains(scene_pos):
                    hovered_id = str(shape_id)
                    hovered_color = item.brush().color().name()
                    break

            self.ui.label.setText(f"X:{int(scene_pos.x())}, Y:{int(scene_pos.y())} Obj ID : {hovered_id}")
            self.ui.frame_2.setStyleSheet(f"background-color: {hovered_color}; border-radius: 4px;")
        elif event.type() == QEvent.Resize:
            self.reposition()

        return False
