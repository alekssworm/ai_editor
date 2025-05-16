from PySide6.QtWidgets import  QGraphicsItem
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
        self.setPen(QPen(Qt.white, 2, Qt.DashLine))

        self.setRect(rect)
        self.handles = []
        self.add_handles()
        self.hide_handles()

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
