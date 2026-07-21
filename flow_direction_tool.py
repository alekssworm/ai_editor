from __future__ import annotations

import math

from PySide6.QtCore import QEvent, QLineF, QObject, QPointF, QRectF, Qt
from PySide6.QtGui import QBrush, QColor, QPainter, QPen, QPolygonF
from PySide6.QtWidgets import QGraphicsItem, QMessageBox

from Activate_disconect_button import deactivate_drawing_mode
from effect_engine.project import normalize_direction


class FlowArrowItem(QGraphicsItem):
    """Non-interactive direction overlay drawn above editor shapes."""

    def __init__(self) -> None:
        super().__init__()
        self._start = QPointF()
        self._end = QPointF()
        self.setAcceptedMouseButtons(Qt.MouseButton.NoButton)
        self.setZValue(10_000)

    def set_line(self, start: QPointF, end: QPointF) -> None:
        self.prepareGeometryChange()
        self._start = QPointF(start)
        self._end = QPointF(end)
        self.update()

    def boundingRect(self) -> QRectF:
        return QRectF(self._start, self._end).normalized().adjusted(-14, -14, 14, 14)

    def paint(self, painter: QPainter, option, widget=None) -> None:
        del option, widget
        line = QLineF(self._start, self._end)
        if line.length() < 1.0:
            return

        color = QColor("#22d3ee")
        pen = QPen(color, 3.0)
        pen.setCosmetic(True)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(pen)
        painter.drawLine(line)

        dx = line.dx() / line.length()
        dy = line.dy() / line.length()
        base = self._end - QPointF(dx * 13.0, dy * 13.0)
        perpendicular = QPointF(-dy * 6.5, dx * 6.5)
        head = QPolygonF([self._end, base + perpendicular, base - perpendicular])
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(color))
        painter.drawPolygon(head)


class FlowDirectionController(QObject):
    """Capture a drag over the selected shape and store a normalized flow vector."""

    def __init__(self, window) -> None:
        super().__init__(window)
        self.window = window
        self.viewport = window.ui.graphicsView.viewport()
        self.viewport.installEventFilter(self)
        self._arrow: FlowArrowItem | None = None
        self._active = False
        self._dragging = False
        self._shape_id: int | None = None
        self._drag_start = QPointF()
        self._button_text = window.ui.settings.text()

    @property
    def active(self) -> bool:
        return self._active

    def _selected_shape(self) -> tuple[int | None, QGraphicsItem | None]:
        try:
            selected = set(self.window.scene.selectedItems())
        except RuntimeError:
            return None, None
        for shape_id, item in self.window.shape_registry.items():
            if item in selected:
                return int(shape_id), item
        return None, None

    def _ensure_arrow(self) -> FlowArrowItem:
        if self._arrow is None:
            self._arrow = FlowArrowItem()
            self.window.scene.addItem(self._arrow)
        return self._arrow

    def _remove_arrow(self) -> None:
        arrow, self._arrow = self._arrow, None
        if arrow is None:
            return
        try:
            if arrow.scene() is not None:
                arrow.scene().removeItem(arrow)
        except RuntimeError:
            pass

    @staticmethod
    def _display_length(item: QGraphicsItem) -> float:
        rect = item.sceneBoundingRect()
        return max(20.0, min(120.0, max(rect.width(), rect.height()) * 0.32))

    def _show_direction(
        self,
        item: QGraphicsItem,
        direction: tuple[float, float],
    ) -> None:
        center = item.sceneBoundingRect().center()
        length = self._display_length(item)
        end = center + QPointF(direction[0] * length, direction[1] * length)
        self._ensure_arrow().set_line(center, end)

    def set_direction(self, shape_id: int, direction) -> bool:
        normalized = normalize_direction(direction)
        item = self.window.shape_registry.get(int(shape_id))
        if normalized is None or item is None:
            return False
        self.window.flow_directions[int(shape_id)] = normalized
        ai_window = getattr(self.window, "ai_window", None)
        if ai_window is not None:
            ai_window.set_shape_direction(shape_id, normalized)
        self._show_direction(item, normalized)
        return True

    def toggle(self) -> None:
        if self._active:
            self.cancel()
        else:
            self.activate()

    def activate(self) -> None:
        shape_id, item = self._selected_shape()
        if shape_id is None or item is None:
            QMessageBox.information(
                self.window,
                "Flow direction",
                "Сначала выберите область на изображении.",
            )
            return

        deactivate_drawing_mode(self.window)
        self._active = True
        self._dragging = False
        self._shape_id = shape_id
        self.viewport.setCursor(Qt.CursorShape.CrossCursor)
        self.viewport.setFocus()
        self.window.ui.settings.setText("cancel flow")
        direction = self.window.flow_directions.get(shape_id, (1.0, 0.0))
        self._show_direction(item, direction)
        self.window.statusBar().showMessage(
            "Зажмите левую кнопку и проведите внутри области по направлению потока; Esc — отмена",
            8000,
        )

    def cancel(self) -> None:
        self._active = False
        self._dragging = False
        self._shape_id = None
        self.viewport.unsetCursor()
        self.window.ui.settings.setText(self._button_text)
        self.window.statusBar().clearMessage()
        self.refresh_for_selection()

    def reset(self) -> None:
        self._active = False
        self._dragging = False
        self._shape_id = None
        self.viewport.unsetCursor()
        self.window.ui.settings.setText(self._button_text)
        self._remove_arrow()

    def refresh_for_selection(self) -> None:
        selected_id, item = self._selected_shape()
        if self._active:
            if selected_id != self._shape_id:
                self.cancel()
            return

        self._remove_arrow()
        if selected_id is None or item is None:
            return
        direction = self.window.flow_directions.get(selected_id)
        normalized = normalize_direction(direction)
        if normalized is not None:
            self._show_direction(item, normalized)

    def _scene_position(self, event) -> QPointF:
        return self.window.ui.graphicsView.mapToScene(event.position().toPoint())

    def _point_in_target(self, point: QPointF) -> bool:
        item = self.window.shape_registry.get(self._shape_id)
        return item is not None and item.contains(item.mapFromScene(point))

    def _finish_drag(self, end: QPointF) -> None:
        dx = end.x() - self._drag_start.x()
        dy = end.y() - self._drag_start.y()
        if math.hypot(dx, dy) >= 3.0 and self._shape_id is not None:
            self.set_direction(self._shape_id, (dx, dy))
            self.window.statusBar().showMessage("Направление потока сохранено", 3000)
        self._active = False
        self._dragging = False
        self._shape_id = None
        self.viewport.unsetCursor()
        self.window.ui.settings.setText(self._button_text)
        self.refresh_for_selection()

    def eventFilter(self, watched, event) -> bool:
        if watched is not self.viewport or not self._active:
            return super().eventFilter(watched, event)

        event_type = event.type()
        if event_type == QEvent.Type.KeyPress and event.key() == Qt.Key.Key_Escape:
            self.cancel()
            return True
        if event_type == QEvent.Type.MouseButtonPress:
            if event.button() == Qt.MouseButton.RightButton:
                self.cancel()
                return True
            if event.button() == Qt.MouseButton.LeftButton:
                point = self._scene_position(event)
                if self._point_in_target(point):
                    self._drag_start = point
                    self._dragging = True
                    self._ensure_arrow().set_line(point, point)
                return True
        if event_type == QEvent.Type.MouseMove and self._dragging:
            self._ensure_arrow().set_line(self._drag_start, self._scene_position(event))
            return True
        if event_type == QEvent.Type.MouseButtonRelease and self._dragging:
            if event.button() == Qt.MouseButton.LeftButton:
                self._finish_drag(self._scene_position(event))
                return True
        return True
