from PySide6.QtCore import QRectF, QPointF, Qt
from PySide6.QtWidgets import QGraphicsSceneMouseEvent
from draw_tools import ResizableRectItem, SelectableCircleItem  # Импортируем оба
from obj_list_logic import add_shape_to_list
from PySide6.QtCore import QTimer  # вверху

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

    def mouseDoubleClickEvent(self, event):
        if self.current_tool:
            # Выключаем инструмент рисования
            self.set_tool(None)
            if self.parent:
                from Activate_disconect_button import deactivate_drawing_mode
                deactivate_drawing_mode(self.parent)


    def mousePressEvent(self, event: QGraphicsSceneMouseEvent):
        if event.button() == Qt.LeftButton:
            color = self.parent.current_shape_color if self.parent else None

            shape_id = self.parent.shape_id_counter
            self.parent.shape_id_counter += 1

            self.drawing = True
            self.start_point = event.scenePos()
            rect = QRectF(self.start_point, self.start_point)

            if self.current_tool == "rectangle":
                self.current_item = ResizableRectItem(rect, color)
            elif self.current_tool == "circle":
                self.current_item = SelectableCircleItem(rect, color, dashed=True)
            else:
                return

            self.scene.addItem(self.current_item)
            self.parent.shape_registry[shape_id] = self.current_item

            # 💡 Проверка вложенности для sub_obj
            parent_id = None
            new_item_rect = self.current_item.sceneBoundingRect()
            for sid, obj in self.parent.shape_registry.items():
                if obj is not self.current_item and obj.sceneBoundingRect().contains(new_item_rect.center()):
                    parent_id = sid
                    break
            self.parent.shape_parents[shape_id] = parent_id

            from obj_list_logic import add_shape_to_list
            add_shape_to_list(self.parent.ui, shape_id, color)

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
