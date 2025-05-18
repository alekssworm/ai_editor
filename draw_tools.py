from PySide6.QtWidgets import QGraphicsItem, QMenu
from PySide6.QtGui import QPen, QBrush, QColor
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QGraphicsEllipseItem

from PySide6.QtCore import QRectF

from PySide6.QtWidgets import QGraphicsRectItem


class ShapeItem:
    """Базовый класс для всех фигур"""
    pass


class ResizeHandleItem(QGraphicsRectItem):
    def __init__(self, parent, corner, size=8):
        super().__init__(-size / 2, -size / 2, size, size, parent)
        self.setBrush(QBrush(Qt.green))

        self.setAcceptedMouseButtons(Qt.LeftButton)
        self.setAcceptHoverEvents(True)
        self.setZValue(1)  # Чтобы всегда была выше

        self.setFlag(QGraphicsItem.ItemSendsGeometryChanges, True)
        self.corner = corner

    def paint(self, painter, option, widget=None):
        super().paint(painter, option, widget)
        if self.isSelected():
            glow_pen = QPen(QColor(255, 255, 255, 180), 2, Qt.DashLine)
            painter.setPen(glow_pen)
            painter.drawRect(self.rect())

    def itemChange(self, change, value):
        if change == QGraphicsItem.ItemPositionChange and self.scene():
            parent = self.parentItem()
            if parent:
                parent.update_from_handle(self, value)
        return super().itemChange(change, value)

    def mousePressEvent(self, event):
        parent = self.parentItem()
        if parent is None:
            return  # защита от падения

        self._drag_start = event.scenePos()
        self._orig_rect = parent.rect()
        event.accept()

    def mouseMoveEvent(self, event):
        parent = self.parentItem()
        if not parent or not hasattr(self, '_orig_rect'):
            return

        delta = event.scenePos() - self._drag_start
        if self.corner == "br":
            new_rect = QRectF(self._orig_rect.topLeft(), self._orig_rect.bottomRight() + delta)
            parent.setRect(new_rect.normalized())
            self.setPos(parent.rect().bottomRight())
        event.accept()


class ResizableRectItem(QGraphicsRectItem,ShapeItem):
    def __init__(self, rect, color=None):
        super().__init__()
        self._updating = False  # ДО setRect
        self.setFlags(QGraphicsItem.ItemIsMovable | QGraphicsItem.ItemIsSelectable)
        self.setBrush(QBrush(color if color else QColor(255, 0, 0, 50)))

        pen = QPen(Qt.transparent)  # По умолчанию без обводки
        pen.setStyle(Qt.NoPen)
        self.setPen(pen)

        self.setRect(rect)
        self.handles = []
        self.add_handles()
        self.hide_handles()
        self.setPen(Qt.NoPen)  # Убирает обводку полностью

        self.fill_visible = True
        self.original_brush = self.brush()  # сохранить оригинальный цвет

    def toggle_fill(self):
        self.set_fill_visibility(not self.fill_visible)

    def set_fill_visibility(self, visible: bool):
        self.fill_visible = visible
        if not visible:
            # Скрыть заливку, оставить контур того же цвета
            self.setBrush(Qt.transparent)
            brush_color = self.original_brush.color() if self.original_brush else QColor(255, 255, 255)
            pen = QPen(brush_color, 2, Qt.SolidLine)
            self.setPen(pen)
        else:
            self.setBrush(self.original_brush)
            self.setPen(QPen(Qt.transparent))  # Или оригинальный стиль

    def add_handles(self):
        br_handle = ResizeHandleItem(self, corner="br")
        br_handle.setPos(self.rect().bottomRight())
        self.handles.append(br_handle)

    def update_from_handle(self, handle, new_pos):
        if handle.corner == "br":
            rect = QRectF(self.rect().topLeft(), self.mapFromScene(new_pos))
            self.setRect(rect.normalized())
            handle.setPos(self.rect().bottomRight())

    def setRect(self, rect):
        if self._updating:
            return
        self._updating = True

        super().setRect(rect)


        self._updating = False

    def update_from_handle(self, handle, new_pos):
        if self._updating:
            return
        self._updating = True

        if handle.corner == "br":
            rect = QRectF(self.rect().topLeft(), self.mapFromScene(new_pos))
            super().setRect(rect.normalized())  # НЕ setRect — super().setRect

            handle.setPos(self.rect().bottomRight())

        self._updating = False

    def show_handles(self):
        for handle in self.handles:
            handle.show()

    def hide_handles(self):
        for handle in self.handles:
            handle.hide()

    def mouseDoubleClickEvent(self, event):
        self.show_handles()
        super().mouseDoubleClickEvent(event)

    def contextMenuEvent(self, event):
        menu = QMenu()
        toggle_action = menu.addAction("Hide/Show fill")
        delete_action = menu.addAction("delete")

        action = menu.exec(event.screenPos())

        if action == toggle_action:
            self.toggle_fill()
        elif action == delete_action:
            scene = self.scene()
            if scene and scene.views():
                main_window = scene.views()[0].window()
                if hasattr(main_window, "shape_registry"):
                    for sid, obj in list(main_window.shape_registry.items()):
                        if obj == self:
                            from obj_list_logic import remove_shape_from_list
                            remove_shape_from_list(main_window.ui, sid)
                            del main_window.shape_registry[sid]
                            break
            scene.removeItem(self)


class SelectableCircleItem(QGraphicsEllipseItem,ShapeItem):
    _id_counter = 0

    def __init__(self, rect: QRectF, color=None, dashed=False):
        super().__init__(rect)
        SelectableCircleItem._id_counter += 1
        self.id = SelectableCircleItem._id_counter

        self.setFlags(QGraphicsItem.ItemIsMovable | QGraphicsItem.ItemIsSelectable)

        if color is not None:
            pen = QPen(color, 2)
            brush = QBrush(color)
        else:
            pen = QPen(Qt.blue, 2)
            brush = QBrush(QColor(0, 0, 255, 50))

        if dashed:
            pen.setStyle(Qt.DashLine)

        self.setPen(pen)
        self.setBrush(brush)

    def finalize(self):
        pen = self.pen()
        pen.setStyle(Qt.SolidLine)
        self.setPen(pen)

    def contextMenuEvent(self, event):
        menu = QMenu()
        toggle_action = menu.addAction("Hide/Show fill")
        delete_action = menu.addAction("delete")

        action = menu.exec(event.screenPos())

        if action == toggle_action:
            self.toggle_fill()
        elif action == delete_action:
            self.scene().removeItem(self)
            if hasattr(self.scene().parent(), "shape_registry"):
                for sid, obj in self.scene().parent().shape_registry.items():
                    if obj == self:
                        del self.scene().parent().shape_registry[sid]
                        break

    def set_fill_visibility(self, visible: bool):
        self.fill_visible = visible
        if not visible:
            # Скрыть заливку, оставить контур того же цвета
            self.setBrush(Qt.transparent)
            brush_color = self.original_brush.color() if self.original_brush else QColor(255, 255, 255)
            pen = QPen(brush_color, 2, Qt.SolidLine)
            self.setPen(pen)
        else:
            self.setBrush(self.original_brush)
            self.setPen(QPen(Qt.transparent))  # Или оригинальный стиль


