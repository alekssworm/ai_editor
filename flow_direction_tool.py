from __future__ import annotations

import copy
import math

from PySide6.QtCore import QEvent, QLineF, QObject, QPointF, QRectF, Qt
from PySide6.QtGui import QBrush, QColor, QPainter, QPainterPath, QPen, QPolygonF
from PySide6.QtWidgets import QGraphicsItem, QMessageBox

from Activate_disconect_button import deactivate_drawing_mode
from effect_engine.project import normalize_direction


class FlowArrowItem(QGraphicsItem):
    """Non-interactive cubic flow curve with an arrow head."""

    def __init__(self) -> None:
        super().__init__()
        self._start = QPointF()
        self._control1 = QPointF()
        self._control2 = QPointF()
        self._end = QPointF()
        self._path = QPainterPath()
        self.setAcceptedMouseButtons(Qt.MouseButton.NoButton)
        self.setZValue(10_000)

    def set_line(self, start: QPointF, end: QPointF) -> None:
        delta = end - start
        self.set_curve(
            start,
            QPointF(start.x() + delta.x() / 3.0, start.y() + delta.y() / 3.0),
            QPointF(
                start.x() + delta.x() * 2.0 / 3.0,
                start.y() + delta.y() * 2.0 / 3.0,
            ),
            end,
        )

    def set_curve(
        self,
        start: QPointF,
        control1: QPointF,
        control2: QPointF,
        end: QPointF,
    ) -> None:
        self.prepareGeometryChange()
        self._start = QPointF(start)
        self._control1 = QPointF(control1)
        self._control2 = QPointF(control2)
        self._end = QPointF(end)
        self._path = QPainterPath(self._start)
        self._path.cubicTo(self._control1, self._control2, self._end)
        self.update()

    def boundingRect(self) -> QRectF:
        return self._path.boundingRect().adjusted(-14, -14, 14, 14)

    def paint(self, painter: QPainter, option, widget=None) -> None:
        del option, widget
        line = QLineF(self._control2, self._end)
        if line.length() < 1.0:
            line = QLineF(self._start, self._end)
        if line.length() < 1.0:
            return

        color = QColor("#22d3ee")
        pen = QPen(color, 3.0)
        pen.setCosmetic(True)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(pen)
        painter.drawPath(self._path)

        dx = line.dx() / line.length()
        dy = line.dy() / line.length()
        base = self._end - QPointF(dx * 13.0, dy * 13.0)
        perpendicular = QPointF(-dy * 6.5, dx * 6.5)
        head = QPolygonF([self._end, base + perpendicular, base - perpendicular])
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(color))
        painter.drawPolygon(head)


class MapZoneItem(QGraphicsItem):
    """Colored non-interactive overlay for one manual material-map zone."""

    def __init__(self, color: QColor) -> None:
        super().__init__()
        self._color = QColor(color)
        self._rect = QRectF()
        self.setAcceptedMouseButtons(Qt.MouseButton.NoButton)
        self.setZValue(9_999)

    def set_circle(self, center: QPointF, radius: float) -> None:
        radius = max(1.0, float(radius))
        self.prepareGeometryChange()
        self._rect = QRectF(
            center.x() - radius,
            center.y() - radius,
            radius * 2.0,
            radius * 2.0,
        )
        self.update()

    def boundingRect(self) -> QRectF:
        return self._rect.adjusted(-3, -3, 3, 3)

    def paint(self, painter: QPainter, option, widget=None) -> None:
        del option, widget
        fill = QColor(self._color)
        fill.setAlpha(45)
        pen = QPen(self._color, 2.0, Qt.PenStyle.DashLine)
        pen.setCosmetic(True)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(pen)
        painter.setBrush(QBrush(fill))
        painter.drawEllipse(self._rect)


class FlowDirectionController(QObject):
    """Capture a drag over the selected shape and store a normalized flow vector."""

    def __init__(self, window) -> None:
        super().__init__(window)
        self.window = window
        self.viewport = window.ui.graphicsView.viewport()
        self.viewport.installEventFilter(self)
        self._arrow: FlowArrowItem | None = None
        self._guide_arrows: list[FlowArrowItem] = []
        self._zone_items: list[MapZoneItem] = []
        self._zone_preview: MapZoneItem | None = None
        self._active = False
        self._dragging = False
        self._append_mode = False
        self._edit_mode = "flow"
        self._shape_id: int | None = None
        self._drag_start = QPointF()
        self._drag_points: list[QPointF] = []
        self._button_text = window.ui.settings.text()
        self._undo_history: dict[int, list[dict]] = {}
        self._redo_history: dict[int, list[dict]] = {}

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
        zone_preview, self._zone_preview = self._zone_preview, None
        arrows = (
            ([arrow] if arrow is not None else [])
            + self._guide_arrows
            + self._zone_items
            + ([zone_preview] if zone_preview is not None else [])
        )
        self._guide_arrows = []
        self._zone_items = []
        for current in arrows:
            try:
                if current.scene() is not None:
                    current.scene().removeItem(current)
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

    def _show_saved_flow(self, shape_id: int, item: QGraphicsItem) -> None:
        self._remove_arrow()
        guides = getattr(self.window, "flow_guides", {}).get(int(shape_id), [])
        for guide in guides:
            try:
                start = QPointF(float(guide["start"][0]), float(guide["start"][1]))
                delta = QPointF(
                    float(guide["end"][0]) - start.x(),
                    float(guide["end"][1]) - start.y(),
                )
                control1_raw = guide.get(
                    "control1",
                    [start.x() + delta.x() / 3.0, start.y() + delta.y() / 3.0],
                )
                control2_raw = guide.get(
                    "control2",
                    [
                        start.x() + delta.x() * 2.0 / 3.0,
                        start.y() + delta.y() * 2.0 / 3.0,
                    ],
                )
                control1 = QPointF(float(control1_raw[0]), float(control1_raw[1]))
                control2 = QPointF(float(control2_raw[0]), float(control2_raw[1]))
                end = QPointF(float(guide["end"][0]), float(guide["end"][1]))
            except (KeyError, TypeError, ValueError, IndexError):
                continue
            arrow = FlowArrowItem()
            arrow.set_curve(start, control1, control2, end)
            self.window.scene.addItem(arrow)
            self._guide_arrows.append(arrow)
        overrides = getattr(self.window, "effect_overrides", {}).get(
            int(shape_id), {}
        )
        zone_styles = {
            "speed_zones": ("#22c55e", "#f59e0b"),
            "obstacle_zones": ("#ef4444", "#ef4444"),
            "foam_zones": ("#f8fafc", "#f8fafc"),
            "mask_add_zones": ("#3b82f6", "#3b82f6"),
            "mask_remove_zones": ("#a855f7", "#a855f7"),
            "depth_zones": ("#06b6d4", "#1e3a8a"),
        }
        for key, colors in zone_styles.items():
            for zone in overrides.get(key, []):
                try:
                    center = QPointF(
                        float(zone["center"][0]), float(zone["center"][1])
                    )
                    radius = float(zone["radius"])
                    value = float(zone.get("value", 1.0))
                except (KeyError, TypeError, ValueError, IndexError):
                    continue
                threshold = 0.5 if key == "depth_zones" else 1.0
                color = colors[0] if value >= threshold else colors[1]
                overlay = MapZoneItem(QColor(color))
                overlay.set_circle(center, radius)
                self.window.scene.addItem(overlay)
                self._zone_items.append(overlay)
        if not self._guide_arrows:
            direction = normalize_direction(
                self.window.flow_directions.get(int(shape_id))
            )
            if direction is not None:
                self._show_direction(item, direction)

    def _snapshot(self, shape_id: int) -> dict:
        directions = getattr(self.window, "flow_directions", {})
        guides = getattr(self.window, "flow_guides", {})
        overrides = getattr(self.window, "effect_overrides", {})
        return {
            "has_direction": shape_id in directions,
            "direction": copy.deepcopy(directions.get(shape_id)),
            "has_guides": shape_id in guides,
            "guides": copy.deepcopy(guides.get(shape_id)),
            "has_overrides": shape_id in overrides,
            "overrides": copy.deepcopy(overrides.get(shape_id)),
        }

    def _record_history(self, shape_id: int) -> None:
        history = self._undo_history.setdefault(int(shape_id), [])
        history.append(self._snapshot(int(shape_id)))
        del history[:-50]
        self._redo_history.pop(int(shape_id), None)

    def _restore_snapshot(self, shape_id: int, snapshot: dict) -> None:
        for name, present_key, value_key in (
            ("flow_directions", "has_direction", "direction"),
            ("flow_guides", "has_guides", "guides"),
            ("effect_overrides", "has_overrides", "overrides"),
        ):
            mapping = getattr(self.window, name)
            if snapshot[present_key]:
                mapping[shape_id] = copy.deepcopy(snapshot[value_key])
            else:
                mapping.pop(shape_id, None)
        direction = normalize_direction(
            getattr(self.window, "flow_directions", {}).get(shape_id)
        )
        ai_window = getattr(self.window, "ai_window", None)
        if ai_window is not None and direction is not None:
            ai_window.set_shape_direction(shape_id, direction)
        item = self.window.shape_registry.get(shape_id)
        if item is not None:
            self._show_saved_flow(shape_id, item)
        scheduler = getattr(self.window, "_schedule_open_preview_refresh", None)
        if callable(scheduler):
            scheduler(shape_id)

    def undo(self) -> bool:
        shape_id = self._shape_id
        if shape_id is None:
            shape_id, _ = self._selected_shape()
        if shape_id is None or not self._undo_history.get(int(shape_id)):
            return False
        shape_id = int(shape_id)
        self._redo_history.setdefault(shape_id, []).append(self._snapshot(shape_id))
        self._restore_snapshot(shape_id, self._undo_history[shape_id].pop())
        self.window.statusBar().showMessage("Flow edit undone.", 3500)
        return True

    def redo(self) -> bool:
        shape_id = self._shape_id
        if shape_id is None:
            shape_id, _ = self._selected_shape()
        if shape_id is None or not self._redo_history.get(int(shape_id)):
            return False
        shape_id = int(shape_id)
        self._undo_history.setdefault(shape_id, []).append(self._snapshot(shape_id))
        self._restore_snapshot(shape_id, self._redo_history[shape_id].pop())
        self.window.statusBar().showMessage("Flow edit restored.", 3500)
        return True

    def set_direction(
        self,
        shape_id: int,
        direction,
        *,
        preserve_guides: bool = False,
        record_history: bool = True,
    ) -> bool:
        normalized = normalize_direction(direction)
        item = self.window.shape_registry.get(int(shape_id))
        if normalized is None or item is None:
            return False
        if record_history:
            self._record_history(int(shape_id))
        self.window.flow_directions[int(shape_id)] = normalized
        if not preserve_guides:
            getattr(self.window, "flow_guides", {}).pop(int(shape_id), None)
        ai_window = getattr(self.window, "ai_window", None)
        if ai_window is not None:
            ai_window.set_shape_direction(shape_id, normalized)
        self._show_saved_flow(int(shape_id), item)
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
        if shape_id not in self.window.flow_directions:
            self.window.flow_directions[shape_id] = (1.0, 0.0)
        self._show_saved_flow(shape_id, item)
        self.window.statusBar().showMessage(
            "Draw a flow curve. Shift: add curve; Ctrl: fast zone; "
            "Ctrl+Shift: slow; Alt: protect; Alt+Shift: foam; "
            "Ctrl+Alt: mask+; Ctrl+Alt+Shift: mask-; "
            "Middle: deep; Shift+Middle: shallow; Delete: clear maps; Esc finishes. "
            "Ctrl+Z/Y: undo/redo.",
            15000,
        )

    def cancel(self) -> None:
        self._active = False
        self._dragging = False
        self._edit_mode = "flow"
        self._drag_points = []
        self._shape_id = None
        self.viewport.unsetCursor()
        self.window.ui.settings.setText(self._button_text)
        self.window.statusBar().clearMessage()
        self.refresh_for_selection()

    def reset(self) -> None:
        self._active = False
        self._dragging = False
        self._edit_mode = "flow"
        self._drag_points = []
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
            self._show_saved_flow(selected_id, item)

    def _scene_position(self, event) -> QPointF:
        return self.window.ui.graphicsView.mapToScene(event.position().toPoint())

    def _point_in_target(self, point: QPointF) -> bool:
        item = self.window.shape_registry.get(self._shape_id)
        return item is not None and item.contains(item.mapFromScene(point))

    @staticmethod
    def _point_at_fraction(points: list[QPointF], fraction: float) -> QPointF:
        if len(points) < 2:
            return QPointF(points[0]) if points else QPointF()
        lengths = [0.0]
        for previous, current in zip(points, points[1:]):
            lengths.append(lengths[-1] + QLineF(previous, current).length())
        target = lengths[-1] * float(fraction)
        for index in range(1, len(points)):
            if lengths[index] < target:
                continue
            segment = max(1e-6, lengths[index] - lengths[index - 1])
            amount = (target - lengths[index - 1]) / segment
            previous, current = points[index - 1], points[index]
            return QPointF(
                previous.x() + (current.x() - previous.x()) * amount,
                previous.y() + (current.y() - previous.y()) * amount,
            )
        return QPointF(points[-1])

    def _curve_points(self, end: QPointF) -> tuple[QPointF, QPointF, QPointF, QPointF]:
        points = [QPointF(point) for point in self._drag_points]
        if not points:
            points = [QPointF(self._drag_start)]
        if QLineF(points[-1], end).length() > 0.5:
            points.append(QPointF(end))
        start = points[0]
        finish = points[-1]
        if len(points) <= 2:
            control1 = QPointF(
                start.x() + (finish.x() - start.x()) / 3.0,
                start.y() + (finish.y() - start.y()) / 3.0,
            )
            control2 = QPointF(
                start.x() + (finish.x() - start.x()) * 2.0 / 3.0,
                start.y() + (finish.y() - start.y()) * 2.0 / 3.0,
            )
        else:
            control1 = self._point_at_fraction(points, 1.0 / 3.0)
            control2 = self._point_at_fraction(points, 2.0 / 3.0)
        return start, control1, control2, finish

    def _update_curve_preview(self, end: QPointF) -> None:
        start, control1, control2, finish = self._curve_points(end)
        self._ensure_arrow().set_curve(start, control1, control2, finish)

    @staticmethod
    def _zone_style(mode: str) -> tuple[str, str, float]:
        return {
            "fast": ("speed_zones", "#22c55e", 1.5),
            "slow": ("speed_zones", "#f59e0b", 0.35),
            "obstacle": ("obstacle_zones", "#ef4444", 1.0),
            "foam": ("foam_zones", "#f8fafc", 1.0),
            "mask_add": ("mask_add_zones", "#3b82f6", 1.0),
            "mask_remove": ("mask_remove_zones", "#a855f7", 1.0),
            "deep": ("depth_zones", "#06b6d4", 0.9),
            "shallow": ("depth_zones", "#1e3a8a", 0.1),
        }[mode]

    def _ensure_zone_preview(self) -> MapZoneItem:
        if self._zone_preview is None:
            _, color, _ = self._zone_style(self._edit_mode)
            self._zone_preview = MapZoneItem(QColor(color))
            self.window.scene.addItem(self._zone_preview)
        return self._zone_preview

    def _finish_zone(self, end: QPointF) -> bool:
        if self._shape_id is None:
            return False
        radius = QLineF(self._drag_start, end).length()
        if radius < 3.0:
            return False
        shape_id = int(self._shape_id)
        key, _, value = self._zone_style(self._edit_mode)
        self._record_history(shape_id)
        if not hasattr(self.window, "effect_overrides"):
            self.window.effect_overrides = {}
        shape_overrides = self.window.effect_overrides.setdefault(shape_id, {})
        zones = list(shape_overrides.get(key, []))
        zones.append(
            {
                "center": [float(self._drag_start.x()), float(self._drag_start.y())],
                "radius": float(radius),
                "value": float(value),
            }
        )
        shape_overrides[key] = zones[-32:]
        item = self.window.shape_registry.get(shape_id)
        if item is not None:
            self._show_saved_flow(shape_id, item)
        labels = {
            "fast": "Fast zone",
            "slow": "Slow zone",
            "obstacle": "Protected zone",
            "foam": "Foam zone",
            "mask_add": "Mask include zone",
            "mask_remove": "Mask exclude zone",
            "deep": "Deep-water zone",
            "shallow": "Shallow-water zone",
        }
        self.window.statusBar().showMessage(
            f"{labels[self._edit_mode]} saved. Continue drawing or press Esc.",
            8000,
        )
        scheduler = getattr(self.window, "_schedule_open_preview_refresh", None)
        if callable(scheduler):
            scheduler(shape_id)
        return True

    def _finish_drag(self, end: QPointF) -> None:
        dx = end.x() - self._drag_start.x()
        dy = end.y() - self._drag_start.y()
        if self._edit_mode != "flow":
            if not self._finish_zone(end):
                item = self.window.shape_registry.get(self._shape_id)
                if item is not None and self._shape_id is not None:
                    self._show_saved_flow(int(self._shape_id), item)
        elif math.hypot(dx, dy) >= 3.0 and self._shape_id is not None:
            shape_id = int(self._shape_id)
            self._record_history(shape_id)
            start, control1, control2, finish = self._curve_points(end)
            guide = {
                "start": [float(start.x()), float(start.y())],
                "control1": [float(control1.x()), float(control1.y())],
                "control2": [float(control2.x()), float(control2.y())],
                "end": [float(finish.x()), float(finish.y())],
            }
            if not hasattr(self.window, "flow_guides"):
                self.window.flow_guides = {}
            guides = list(self.window.flow_guides.get(shape_id, []))
            guides = guides + [guide] if self._append_mode else [guide]
            guides = guides[-8:]
            self.window.flow_guides[shape_id] = guides
            average_x = sum(
                item["end"][0] - item["start"][0] for item in guides[-8:]
            )
            average_y = sum(
                item["end"][1] - item["start"][1] for item in guides[-8:]
            )
            self.set_direction(
                shape_id,
                (average_x, average_y),
                preserve_guides=True,
                record_history=False,
            )
            self.window.statusBar().showMessage(
                f"Flow saved: {len(self.window.flow_guides[shape_id])} guide(s). "
                "Shift+drag adds another; Esc or the Flow button finishes.",
                8000,
            )
            scheduler = getattr(self.window, "_schedule_open_preview_refresh", None)
            if callable(scheduler):
                scheduler(shape_id)
        else:
            item = self.window.shape_registry.get(self._shape_id)
            if item is not None and self._shape_id is not None:
                self._show_saved_flow(int(self._shape_id), item)
        self._dragging = False
        self._append_mode = False
        self._edit_mode = "flow"
        self._drag_points = []

    def eventFilter(self, watched, event) -> bool:
        if watched is not self.viewport or not self._active:
            return super().eventFilter(watched, event)

        event_type = event.type()
        if event_type == QEvent.Type.KeyPress:
            modifiers = event.modifiers()
            control = bool(modifiers & Qt.KeyboardModifier.ControlModifier)
            shift = bool(modifiers & Qt.KeyboardModifier.ShiftModifier)
            if control and event.key() == Qt.Key.Key_Z:
                return self.redo() if shift else self.undo()
            if control and event.key() == Qt.Key.Key_Y:
                return self.redo()
        if event_type == QEvent.Type.KeyPress and event.key() == Qt.Key.Key_Escape:
            self.cancel()
            return True
        if event_type == QEvent.Type.KeyPress and event.key() == Qt.Key.Key_Delete:
            if self._shape_id is not None:
                shape_id = int(self._shape_id)
                self._record_history(shape_id)
                getattr(self.window, "flow_guides", {}).pop(shape_id, None)
                getattr(self.window, "effect_overrides", {}).pop(shape_id, None)
                item = self.window.shape_registry.get(shape_id)
                if item is not None:
                    self._show_saved_flow(shape_id, item)
                self.window.statusBar().showMessage(
                    "Manual flow curves and map corrections cleared.", 5000
                )
            return True
        if event_type == QEvent.Type.MouseButtonPress:
            if event.button() == Qt.MouseButton.RightButton:
                self.cancel()
                return True
            if event.button() in {
                Qt.MouseButton.LeftButton,
                Qt.MouseButton.MiddleButton,
            }:
                point = self._scene_position(event)
                if self._point_in_target(point):
                    modifiers = event.modifiers()
                    has_shift = bool(
                        modifiers & Qt.KeyboardModifier.ShiftModifier
                    )
                    has_control = bool(
                        modifiers & Qt.KeyboardModifier.ControlModifier
                    )
                    has_alt = bool(modifiers & Qt.KeyboardModifier.AltModifier)
                    if event.button() == Qt.MouseButton.MiddleButton:
                        self._edit_mode = "shallow" if has_shift else "deep"
                    elif has_alt and has_control:
                        self._edit_mode = (
                            "mask_remove" if has_shift else "mask_add"
                        )
                    elif has_alt:
                        self._edit_mode = "foam" if has_shift else "obstacle"
                    elif has_control:
                        self._edit_mode = "slow" if has_shift else "fast"
                    else:
                        self._edit_mode = "flow"
                    self._drag_start = point
                    self._drag_points = [QPointF(point)]
                    self._dragging = True
                    self._append_mode = self._edit_mode == "flow" and has_shift
                    if self._edit_mode == "flow":
                        self._ensure_arrow().set_line(point, point)
                    else:
                        self._ensure_zone_preview().set_circle(point, 1.0)
                return True
        if event_type == QEvent.Type.MouseMove and self._dragging:
            point = self._scene_position(event)
            if self._edit_mode == "flow":
                if QLineF(self._drag_points[-1], point).length() >= 2.0:
                    self._drag_points.append(QPointF(point))
                self._update_curve_preview(point)
            else:
                self._ensure_zone_preview().set_circle(
                    self._drag_start,
                    QLineF(self._drag_start, point).length(),
                )
            return True
        if event_type == QEvent.Type.MouseButtonRelease and self._dragging:
            if event.button() in {
                Qt.MouseButton.LeftButton,
                Qt.MouseButton.MiddleButton,
            }:
                self._finish_drag(self._scene_position(event))
                return True
        return True
