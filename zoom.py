from PySide6.QtWidgets import QGraphicsView
from PySide6.QtGui import QWheelEvent, QMouseEvent
from PySide6.QtCore import Qt

class GraphicsViewWithZoom(QGraphicsView):
    """Расширенный QGraphicsView с поддержкой зума и панорамирования"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setDragMode(QGraphicsView.NoDrag)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.zoom_factor = 1.15
        self.min_zoom = 0.5
        self.max_zoom = 3.0
        self.current_zoom = 1.0
        self.is_panning = False

    def wheelEvent(self, event: QWheelEvent):
        factor = self.zoom_factor
        if event.modifiers() == Qt.ControlModifier:
            factor = self.zoom_factor  # Точный зум с Ctrl
        else:
            factor = 1.05  # Мягкий зум без Ctrl

        if event.angleDelta().y() > 0:
            if self.current_zoom < self.max_zoom:
                self.scale(factor, factor)
                self.current_zoom *= factor
        else:
            if self.current_zoom > self.min_zoom:
                self.scale(1 / factor, 1 / factor)
                self.current_zoom /= factor
