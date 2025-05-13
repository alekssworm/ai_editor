from PySide6.QtWidgets import QWidget, QLabel, QFrame, QHBoxLayout
from PySide6.QtCore import QObject, Qt, QEvent


class NavigationOverlay(QObject):
    def __init__(self, parent_view, main_window):
        super().__init__()
        self.parent_view = parent_view
        self.main_window = main_window

        self.widget = QWidget(parent_view.viewport())
        self.widget.setAttribute(Qt.WA_TranslucentBackground)
        self.widget.setAttribute(Qt.WA_TransparentForMouseEvents, False)
        self.widget.setWindowFlags(Qt.FramelessWindowHint)
        self.widget.setStyleSheet("background-color: rgba(0, 0, 0, 160); border-radius: 6px;")
        self.widget.setFixedSize(280, 32)

        layout = QHBoxLayout(self.widget)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(0)
        layout.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)

        # Один текст без отступов
        self.label = QLabel("X:0 Y:0 ID:0 color:", self.widget)
        self.label.setStyleSheet("color: white; background: transparent;")
        layout.addWidget(self.label)

        # Цветной квадрат — вплотную
        self.color_frame = QFrame(self.widget)
        self.color_frame.setFixedSize(12, 12)
        self.color_frame.setStyleSheet("background-color: transparent; border-radius: 2px;")
        layout.addWidget(self.color_frame)

        self.widget.setLayout(layout)
        self.widget.show()
        self.reposition()

        self.parent_view.viewport().installEventFilter(self)
        self.parent_view.installEventFilter(self)

    def reposition(self):
        view_size = self.parent_view.viewport().size()
        x = 10
        y = view_size.height() - self.widget.height() - 10
        self.widget.move(x, y)
        self.widget.raise_()

    def update_position(self, scene_pos):
        hovered_id = "0"
        hovered_color = "transparent"

        for shape_id, item in self.main_window.shape_registry.items():
            if item.contains(item.mapFromScene(scene_pos)):
                hovered_id = str(shape_id)
                hovered_color = item.brush().color().name()
                break

        self.label.setText(
            f"X:{int(scene_pos.x())} Y:{int(scene_pos.y())} ID:{hovered_id} color:"
        )
        self.color_frame.setStyleSheet(
            f"background-color: {hovered_color}; border-radius: 2px;"
        )

    def eventFilter(self, source, event):
        if event.type() == QEvent.Resize:
            self.reposition()
        return False
