from PySide6.QtWidgets import QGraphicsRectItem, QGraphicsItem
from PySide6.QtGui import QPen, QBrush, QColor
from PySide6.QtCore import Qt

class SelectableRectItem(QGraphicsRectItem):
    _id_counter = 0

    def __init__(self, rect, color=None):
        super().__init__(rect)
        SelectableRectItem._id_counter += 1
        self.id = SelectableRectItem._id_counter
        self.setFlags(QGraphicsItem.ItemIsMovable | QGraphicsItem.ItemIsSelectable)

        if color is not None:
            self.setPen(QPen(color, 2))
            self.setBrush(QBrush(color))
        else:
            self.setPen(QPen(Qt.red, 2))
            self.setBrush(QBrush(QColor(255, 0, 0, 50)))


from PySide6.QtWidgets import QGraphicsEllipseItem, QGraphicsItem
from PySide6.QtGui import QPen, QBrush, QColor
from PySide6.QtCore import Qt, QRectF


class SelectableCircleItem(QGraphicsEllipseItem):
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
