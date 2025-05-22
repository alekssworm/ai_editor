from PySide6.QtCore import QRectF, QPointF, Qt
from PySide6.QtWidgets import QGraphicsSceneMouseEvent
from draw_tools import ResizableRectItem, SelectableCircleItem, SelectablePolygonItem  # Импортируем оба
from obj_list_logic import add_shape_to_list
from PySide6.QtCore import QTimer  # вверху

from PySide6.QtCore import QRectF, QPointF, Qt, QTimer
from PySide6.QtGui import QPolygonF, QColor, QPen
from PySide6.QtWidgets import (
    QGraphicsSceneMouseEvent, QGraphicsEllipseItem,
    QGraphicsPolygonItem, QGraphicsLineItem
)

from draw_tools import ResizableRectItem, SelectableCircleItem
from obj_list_logic import add_shape_to_list


class DrawingToolController:
    def __init__(self, scene, parent=None):
        self.scene = scene
        self.parent = parent
        self.drawing = False
        self.start_point = QPointF()
        self.current_item = None
        self.current_tool = None

        # Для polygon
        self.polygon_points = []
        self.polygon_items = []
        self.temp_lines = []

    def set_tool(self, tool_name):
        self.current_tool = tool_name
        if tool_name != "polygon":
            self.clear_polygon_temp()

    def clear_polygon_temp(self):
        for item in self.polygon_items + self.temp_lines:
            self.scene.removeItem(item)
        self.polygon_points.clear()
        self.polygon_items.clear()
        self.temp_lines.clear()

    def mousePressEvent(self, event: QGraphicsSceneMouseEvent):
        if event.button() != Qt.LeftButton:
            return

        color = self.parent.current_shape_color if self.parent else QColor(255, 0, 0, 50)
        line_color = QColor(color)
        line_color.setAlpha(255)
        fill_color = QColor(color)
        fill_color.setAlpha(100)

        if self.current_tool == "rectangle" or self.current_tool == "circle":
            shape_id = self.parent.shape_id_counter
            self.parent.shape_id_counter += 1

            self.drawing = True
            self.start_point = event.scenePos()
            rect = QRectF(self.start_point, self.start_point)

            if self.current_tool == "rectangle":
                self.current_item = ResizableRectItem(rect, color)
            elif self.current_tool == "circle":
                self.current_item = SelectableCircleItem(rect, color, dashed=True)

            self.scene.addItem(self.current_item)
            self.parent.shape_registry[shape_id] = self.current_item

            parent_id = None
            new_item_rect = self.current_item.sceneBoundingRect()
            for sid, obj in self.parent.shape_registry.items():
                if obj is not self.current_item and obj.sceneBoundingRect().contains(new_item_rect.center()):
                    parent_id = sid
                    break
            self.parent.shape_parents[shape_id] = parent_id
            add_shape_to_list(self.parent.ui, shape_id, color)

        elif self.current_tool == "polygon":
            point = event.scenePos()
            self.polygon_points.append(point)

            dot = QGraphicsEllipseItem(-5, -5, 10, 10)
            dot.setPos(point)
            dot.setBrush(line_color)
            dot.setPen(Qt.NoPen)
            self.scene.addItem(dot)
            self.polygon_items.append(dot)

            if len(self.polygon_points) > 1:
                line = QGraphicsLineItem(
                    self.polygon_points[-2].x(), self.polygon_points[-2].y(),
                    point.x(), point.y()
                )
                pen = QPen(line_color, 5)
                line.setPen(pen)
                self.scene.addItem(line)
                self.temp_lines.append(line)

                if len(self.polygon_points) >= 3:
                    dist = (point - self.polygon_points[0]).manhattanLength()
                    if dist < 15:
                        self.finish_polygon()

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
                def safe_finalize():
                    if hasattr(self.current_item, "finalize"):
                        try:
                            self.current_item.finalize()
                        except Exception as e:
                            print("Finalize error:", e)
                QTimer.singleShot(0, safe_finalize)

            self.drawing = False
            self.current_item = None

    def mouseDoubleClickEvent(self, event):
        if self.current_tool == "polygon":
            self.finish_polygon()
        else:
            # Завершение других инструментов
            self.set_tool(None)
            if self.parent:
                from Activate_disconect_button import deactivate_drawing_mode
                deactivate_drawing_mode(self.parent)

    def finish_polygon(self):
        polygon = SelectablePolygonItem(QPolygonF(self.polygon_points), QColor(255, 0, 0, 100))
        fill_color = self.parent.current_shape_color if self.parent else QColor(255, 0, 0, 50)
        polygon.setBrush(fill_color)

        polygon.setPen(QPen(Qt.transparent))
        self.scene.addItem(polygon)

        shape_id = self.parent.shape_id_counter
        self.parent.shape_id_counter += 1
        self.parent.shape_registry[shape_id] = polygon
        self.parent.shape_parents[shape_id] = None
        add_shape_to_list(self.parent.ui, shape_id, QColor(255, 0, 0, 100))

        parent_id = None
        polygon_rect = polygon.sceneBoundingRect()
        for sid, obj in self.parent.shape_registry.items():
            if obj is not polygon and obj.sceneBoundingRect().contains(polygon_rect.center()):
                parent_id = sid
                break

        self.parent.shape_parents[shape_id] = parent_id

        self.clear_polygon_temp()
