def load_scene(self):
    from draw_tools import ResizableRectItem, SelectableCircleItem
    from obj_list_logic import add_shape_to_list
    from PySide6.QtWidgets import QFileDialog, QGraphicsPixmapItem
    from PySide6.QtGui import QColor, QPixmap
    from PySide6.QtCore import QRectF, Qt
    import json, os

    # 1. Выбор файла
    file_path, _ = QFileDialog.getOpenFileName(self, "Загрузить shapes.json", "", "JSON файлы (*.json)")
    if not file_path:
        return

    # 2. Загрузка JSON
    with open(file_path, "r", encoding="utf-8") as f:
        full_data = json.load(f)

    shapes = full_data.get("shapes", [])
    bg_path = full_data.get("background", "")

    # 3. Очистка сцены
    self.scene.clear()
    self.shape_registry.clear()
    self.shape_id_counter = 1

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
        x, y = shape["x"], shape["y"]
        w, h = shape["width"], shape["height"]
        color = QColor(shape["color"])
        color.setAlpha(50)

        if item_type == "Rectangle":
            item = ResizableRectItem(QRectF(x, y, w, h), color)
        elif item_type == "Circle":
            item = SelectableCircleItem(QRectF(x, y, w, h), color)
        else:
            continue

        self.scene.addItem(item)
        if shape_id is None:
            shape_id = self.shape_id_counter

        self.shape_registry[shape_id] = item
        add_shape_to_list(self.ui, shape_id, color)

        if shape_id >= self.shape_id_counter:
            self.shape_id_counter = shape_id + 1
