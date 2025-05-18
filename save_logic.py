import os
import json
from PySide6.QtWidgets import QFileDialog, QGraphicsPixmapItem
from PySide6.QtGui import QImage, QPainter, Qt, QPainterPath
from PySide6.QtCore import QPointF
from draw_tools import SelectableCircleItem, ResizableRectItem, ShapeItem

def save_outputs(self):
    from draw_tools import ShapeItem, SelectableCircleItem
    folder = QFileDialog.getExistingDirectory(self, "Выберите папку для сохранения")
    if not folder:
        print("❌ Сохранение отменено.")
        return

    rect = self.scene.sceneRect()
    size = rect.size().toSize()

    background = next((item for item in self.scene.items() if isinstance(item, QGraphicsPixmapItem)), None)
    if not background:
        print("❌ Фон не найден.")
        return

    original_image_path = background.data(Qt.UserRole) if background.data(Qt.UserRole) else ""
    original_image = background.pixmap().toImage()
    clean_parent_image = QImage(original_image)  # ← для родителей без sub-объектов

    # Подготовка сцены без перьев
    full_scene = QImage(size, QImage.Format_ARGB32)
    full_scene.fill(Qt.transparent)

    shape_pen_backup = {}
    for item in self.scene.items():
        if isinstance(item, ShapeItem):
            shape_pen_backup[item] = item.pen()
            item.setPen(Qt.NoPen)

    painter = QPainter(full_scene)
    self.scene.render(painter)
    painter.end()

    for item, pen in shape_pen_backup.items():
        item.setPen(pen)

    image_without_shapes = QImage(full_scene)
    painter = QPainter(image_without_shapes)
    painter.setCompositionMode(QPainter.CompositionMode_Clear)

    shape_data = []
    index = 1

    children = []
    parents = []

    for item in reversed(self.scene.items()):
        if not isinstance(item, ShapeItem):
            continue
        shape_id = next((sid for sid, obj in self.shape_registry.items() if obj == item), None)
        if shape_id and self.shape_parents.get(shape_id):
            children.append((shape_id, item))
        else:
            parents.append((shape_id, item))

    # 1. Вырезаем sub-объекты и делаем "дыры" в clean_parent_image
    for shape_id, item in children:
        shape_rect = item.sceneBoundingRect().toRect()
        brush_color = item.brush().color().name()
        item_type = "Circle" if isinstance(item, SelectableCircleItem) else "Rectangle"

        # Дырка в image_without_shapes
        if item_type == "Circle":
            path = QPainterPath()
            path.addEllipse(shape_rect)
            painter.setClipPath(path)
            painter.fillPath(path, Qt.transparent)
        else:
            painter.fillRect(shape_rect, Qt.transparent)

        # Дырка в clean_parent_image
        painter_on_parent = QPainter(clean_parent_image)
        painter_on_parent.setCompositionMode(QPainter.CompositionMode_Clear)
        if item_type == "Circle":
            path = QPainterPath()
            path.addEllipse(shape_rect)
            painter_on_parent.setClipPath(path)
            painter_on_parent.fillPath(path, Qt.transparent)
        else:
            painter_on_parent.fillRect(shape_rect, Qt.transparent)
        painter_on_parent.end()

        # PNG из original_image
        cut_size = shape_rect.size()
        cut_image = QImage(cut_size, QImage.Format_ARGB32)
        cut_image.fill(Qt.transparent)
        cut_painter = QPainter(cut_image)
        cut_painter.setPen(Qt.NoPen)
        offset = QPointF(-shape_rect.x(), -shape_rect.y())
        cut_painter.drawImage(offset, original_image)
        cut_painter.end()

        cut_image.save(os.path.join(folder, f"shape_{index}.png"))
        shape_data.append({
            "id": shape_id,
            "type": item_type,
            "x": int(shape_rect.x()),
            "y": int(shape_rect.y()),
            "width": int(shape_rect.width()),
            "height": int(shape_rect.height()),
            "color": brush_color,
            "parent_id": self.shape_parents.get(shape_id)
        })
        index += 1

    # 2. Родители — вырезаются из clean_parent_image
    for shape_id, item in parents:
        shape_rect = item.sceneBoundingRect().toRect()
        brush_color = item.brush().color().name()
        item_type = "Circle" if isinstance(item, SelectableCircleItem) else "Rectangle"

        cut_size = shape_rect.size()
        cut_image = QImage(cut_size, QImage.Format_ARGB32)
        cut_image.fill(Qt.transparent)

        cut_painter = QPainter(cut_image)
        cut_painter.setPen(Qt.NoPen)
        offset = QPointF(-shape_rect.x(), -shape_rect.y())
        cut_painter.drawImage(offset, clean_parent_image)
        cut_painter.end()

        cut_image.save(os.path.join(folder, f"shape_{index}.png"))
        shape_data.append({
            "id": shape_id,
            "type": item_type,
            "x": int(shape_rect.x()),
            "y": int(shape_rect.y()),
            "width": int(shape_rect.width()),
            "height": int(shape_rect.height()),
            "color": brush_color,
            "parent_id": self.shape_parents.get(shape_id)
        })
        index += 1

    painter.end()
    image_without_shapes.save(os.path.join(folder, "image_without_shape_area.png"))

    with open(os.path.join(folder, "shapes.json"), "w", encoding="utf-8") as f:
        json.dump({
            "background": original_image_path,
            "shapes": shape_data
        }, f, indent=4)

    print(f"✅ Сохранено {index - 1} фигур.")

