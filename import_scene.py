from PySide6.QtCore import QPointF
from PySide6.QtGui import QPolygonF

from draw_tools import SelectablePolygonItem
from effect_engine.project import (
    load_project,
    project_effect_overrides,
    project_flow_direction,
    project_flow_guides,
)


def load_scene(self):
    from draw_tools import ResizableRectItem, SelectableCircleItem
    from obj_list_logic import add_shape_to_list
    from PySide6.QtWidgets import QFileDialog, QGraphicsPixmapItem, QMessageBox
    from PySide6.QtGui import QColor, QPixmap
    from PySide6.QtCore import QRectF, Qt
    import os

    # 1. Выбор файла
    file_path, _ = QFileDialog.getOpenFileName(self, "Загрузить shapes.json", "", "JSON файлы (*.json)")
    if not file_path:
        return

    # 2. Загрузка JSON
    try:
        _, full_data = load_project(file_path)
    except (OSError, ValueError) as error:
        QMessageBox.critical(self, "Project error", str(error))
        return

    shapes = full_data.get("shapes", [])
    bg_path = full_data.get("background", "")
    project_dir = os.path.dirname(os.path.abspath(file_path))
    if bg_path and not os.path.isabs(bg_path):
        bg_path = os.path.join(project_dir, bg_path)

    try:
        if not isinstance(shapes, list):
            raise ValueError("Project field 'shapes' must be a list")
        seen_ids = set()
        for index, shape in enumerate(shapes, start=1):
            if not isinstance(shape, dict):
                raise ValueError(f"Shape #{index} must be an object")
            shape_id = int(shape.get("id", index))
            if shape_id in seen_ids:
                raise ValueError(f"Duplicate shape id: {shape_id}")
            seen_ids.add(shape_id)
            shape_type = str(shape.get("type") or "")
            if shape_type not in {"Rectangle", "Circle", "Polygon"}:
                raise ValueError(f"Unsupported shape type: {shape_type!r}")
            color = QColor(str(shape.get("color") or ""))
            if not color.isValid():
                raise ValueError(f"Invalid color for shape {shape_id}")
            if shape_type == "Polygon":
                points = shape.get("points")
                if not isinstance(points, list) or len(points) < 3:
                    raise ValueError(f"Polygon {shape_id} needs at least 3 points")
                for point in points:
                    float(point["x"])
                    float(point["y"])
            else:
                float(shape["x"])
                float(shape["y"])
                if float(shape["width"]) <= 0 or float(shape["height"]) <= 0:
                    raise ValueError(f"Shape {shape_id} has invalid size")
        if not bg_path or not os.path.isfile(bg_path):
            raise ValueError(f"Background image not found: {bg_path or '<empty>'}")
        background_pixmap = QPixmap(bg_path)
        if background_pixmap.isNull():
            raise ValueError(f"Background image could not be decoded: {bg_path}")
    except (KeyError, TypeError, ValueError) as error:
        QMessageBox.critical(self, "Project error", str(error))
        return

    if getattr(self, "shape_registry", None):
        answer = QMessageBox.question(
            self,
            "Replace project",
            "Replace the current project? Unsaved changes will be lost.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return

    # Remember paths only after the complete project has passed validation.
    self.current_shapes_json_path = file_path
    self.current_project_folder = project_dir

    # 3. Очистка сцены
    if hasattr(self, "flow_direction_controller"):
        self.flow_direction_controller.reset()
    self.scene.clear()
    self.shape_registry.clear()
    self.shape_id_counter = 1
    self.shape_parents = {}
    self.flow_directions = {}
    self.flow_guides = {}
    self.effect_overrides = {}
    self.ui.listWidget.clear()
    if hasattr(self, "ai_window"):
        self.ai_window.reset_project_state()

    # 4. Добавление фонового изображения
    if bg_path and os.path.exists(bg_path):
        bg_item = QGraphicsPixmapItem(background_pixmap)
        bg_item.setData(Qt.UserRole, bg_path)
        self.scene.addItem(bg_item)
        self.ui.graphicsView.fitInView(self.scene.itemsBoundingRect(), Qt.KeepAspectRatio)

    # 5. Восстановление фигур
    for shape in shapes:
        shape_id = int(shape.get("id", self.shape_id_counter))
        item_type = shape.get("type")
        color = QColor(shape["color"])
        color.setAlpha(50)

        parent_id = shape.get("parent_id")
        self.shape_parents[shape_id] = parent_id

        if item_type == "Rectangle":
            x, y = shape["x"], shape["y"]
            w, h = shape["width"], shape["height"]
            item = ResizableRectItem(QRectF(x, y, w, h), color)
        elif item_type == "Circle":
            x, y = shape["x"], shape["y"]
            w, h = shape["width"], shape["height"]
            item = SelectableCircleItem(QRectF(x, y, w, h), color)
        elif item_type == "Polygon":
            points = shape.get("points", [])
            if len(points) < 3:
                continue
            polygon = QPolygonF([QPointF(p["x"], p["y"]) for p in points])
            item = SelectablePolygonItem(polygon, color)

        else:
            continue

        self.scene.addItem(item)
        self.shape_registry[shape_id] = item
        direction = project_flow_direction(full_data, shape_id)
        if direction is not None:
            self.flow_directions[shape_id] = direction
        guides = project_flow_guides(full_data, shape_id)
        if guides:
            self.flow_guides[shape_id] = guides
        overrides = project_effect_overrides(full_data, shape_id)
        if overrides:
            self.effect_overrides[shape_id] = overrides
        add_shape_to_list(self.ui, shape_id, color)
        if hasattr(self, "ai_window"):
            self.ai_window.add_shape_card(shape_id, item_type, color.name())
            if direction is not None:
                self.ai_window.set_shape_direction(shape_id, direction)

        if shape_id >= self.shape_id_counter:
            self.shape_id_counter = shape_id + 1

    if hasattr(self, "ai_window"):
        self.ai_window.restore_shape_cards_data(full_data.get("shape_cards", []))
        for card in self.ai_window.collect_shape_cards_data():
            motion = card.get("motion")
            if isinstance(motion, dict):
                self._sync_ai_motion(card.get("id"), motion)
    if hasattr(self, "flow_direction_controller"):
        self.flow_direction_controller.refresh_for_selection()
