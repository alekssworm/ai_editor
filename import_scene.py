from PySide6.QtCore import QPointF
from PySide6.QtGui import QPolygonF

from draw_tools import SelectablePolygonItem
from effect_engine.project import load_project, project_flow_direction


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

    # запомним путь для AI render только после успешной проверки
    self.current_shapes_json_path = file_path

    shapes = full_data.get("shapes", [])
    bg_path = full_data.get("background", "")
    project_dir = os.path.dirname(os.path.abspath(file_path))
    if bg_path and not os.path.isabs(bg_path):
        bg_path = os.path.join(project_dir, bg_path)
    self.current_project_folder = project_dir

    # 3. Очистка сцены
    if hasattr(self, "flow_direction_controller"):
        self.flow_direction_controller.reset()
    self.scene.clear()
    self.shape_registry.clear()
    self.shape_id_counter = 1
    self.shape_parents = {}
    self.flow_directions = {}
    self.ui.listWidget.clear()
    if hasattr(self, "ai_window"):
        self.ai_window.reset_project_state()

    # 4. Добавление фонового изображения
    if bg_path and os.path.exists(bg_path):
        pixmap = QPixmap(bg_path)
        bg_item = QGraphicsPixmapItem(pixmap)
        bg_item.setData(Qt.UserRole, bg_path)
        self.scene.addItem(bg_item)
        self.ui.graphicsView.fitInView(self.scene.itemsBoundingRect(), Qt.KeepAspectRatio)

    # 5. Восстановление фигур
    for shape in shapes:
        shape_id = shape.get("id")
        item_type = shape.get("type")
        if shape_id is None:
            shape_id = self.shape_id_counter
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
        add_shape_to_list(self.ui, shape_id, color)
        if hasattr(self, "ai_window"):
            self.ai_window.add_shape_card(shape_id, item_type, color.name())

        if shape_id >= self.shape_id_counter:
            self.shape_id_counter = shape_id + 1

    if hasattr(self, "ai_window"):
        self.ai_window.restore_shape_cards_data(full_data.get("shape_cards", []))
    if hasattr(self, "flow_direction_controller"):
        self.flow_direction_controller.refresh_for_selection()
