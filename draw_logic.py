from PySide6.QtCore import QRectF, QPointF, Qt
from PySide6.QtWidgets import QGraphicsSceneMouseEvent
from draw_tools import SelectableRectItem, SelectableCircleItem  # Импортируем оба

class DrawingToolController:
    def __init__(self, scene,parent=None):
        self.scene = scene
        self.parent = parent
        self.drawing = False
        self.start_point = QPointF()
        self.current_item = None
        self.current_tool = None  # "rectangle", "circle"

    def set_tool(self, tool_name):
        self.current_tool = tool_name

    def mousePressEvent(self, event: QGraphicsSceneMouseEvent):
        if event.button() == Qt.LeftButton:
            color = self.parent.current_shape_color if self.parent else None
            if self.current_tool == "rectangle":
                self.drawing = True
                self.start_point = event.scenePos()
                rect = QRectF(self.start_point, self.start_point)
                self.current_item = SelectableRectItem(rect, color)
                self.scene.addItem(self.current_item)

            elif self.current_tool == "circle":
                self.drawing = True
                self.start_point = event.scenePos()
                rect = QRectF(self.start_point, self.start_point)
                self.current_item = SelectableCircleItem(rect, color, dashed=True)
                self.scene.addItem(self.current_item)

    def mouseMoveEvent(self, event: QGraphicsSceneMouseEvent):
        if self.drawing and self.current_item:
            end_point = event.scenePos()
            if self.current_tool == "rectangle":
                rect = QRectF(self.start_point, end_point).normalized()
                self.current_item.setRect(rect)
            elif self.current_tool == "circle":
                center = self.start_point
                radius = (end_point - center).manhattanLength()
                rect = QRectF(center.x() - radius, center.y() - radius, radius * 2, radius * 2)
                self.current_item.setRect(rect)

    def mouseReleaseEvent(self, event: QGraphicsSceneMouseEvent):
        if self.drawing:
            if self.current_tool == "circle" and self.current_item:
                self.current_item.finalize()
            self.drawing = False
            self.current_item = None
