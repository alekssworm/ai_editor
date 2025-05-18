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

    background = next((item for item in self.scene.items() if isinstance(item, QGraphicsPixmapItem)), None)
    if not background:
        print("❌ Фон не найден.")
        return

    original_image_path = background.data(Qt.UserRole) if background.data(Qt.UserRole) else ""
    original_image = background.pixmap().toImage()
    without_shape_image = QImage(original_image)
    clean_parent_image = QImage(original_image)

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

    # Сначала sub_obj
    for shape_id, item in children:
        shape_rect = item.sceneBoundingRect().toRect()
        brush_color = item.brush().color().name()
        item_type = "Circle" if isinstance(item, SelectableCircleItem) else "Rectangle"

        cut_size = shape_rect.size()
        cut_image = QImage(cut_size, QImage.Format_ARGB32)
        cut_image.fill(Qt.transparent)
        cut_painter = QPainter(cut_image)
        cut_painter.setPen(Qt.NoPen)
        offset = QPointF(-shape_rect.x(), -shape_rect.y())
        cut_painter.drawImage(offset, original_image)

        if item_type == "Circle":
            path = QPainterPath()
            path.addEllipse(0, 0, cut_size.width(), cut_size.height())
            cut_painter.setCompositionMode(QPainter.CompositionMode_Clear)
            mask = QPainterPath()
            mask.addRect(0, 0, cut_size.width(), cut_size.height())
            mask = mask.subtracted(path)
            cut_painter.fillPath(mask, Qt.transparent)

        cut_painter.end()
        cut_image.save(os.path.join(folder, f"shape_{index}.png"))

        # Пробиваем в without_shape_image
        for target in [without_shape_image, clean_parent_image]:
            painter_clear = QPainter(target)
            painter_clear.setCompositionMode(QPainter.CompositionMode_Clear)
            if item_type == "Circle":
                path = QPainterPath()
                path.addEllipse(shape_rect)
                painter_clear.setClipPath(path)
                painter_clear.fillPath(path, Qt.transparent)
            else:
                painter_clear.fillRect(shape_rect, Qt.transparent)
            painter_clear.end()

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

    # Затем parents
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

        if item_type == "Circle":
            path = QPainterPath()
            path.addEllipse(0, 0, cut_size.width(), cut_size.height())
            cut_painter.setCompositionMode(QPainter.CompositionMode_Clear)
            mask = QPainterPath()
            mask.addRect(0, 0, cut_size.width(), cut_size.height())
            mask = mask.subtracted(path)
            cut_painter.fillPath(mask, Qt.transparent)

        cut_painter.end()
        cut_image.save(os.path.join(folder, f"shape_{index}.png"))

        # Вырезаем из without_shape_image тоже
        painter_clear = QPainter(without_shape_image)
        painter_clear.setCompositionMode(QPainter.CompositionMode_Clear)
        if item_type == "Circle":
            path = QPainterPath()
            path.addEllipse(shape_rect)
            painter_clear.setClipPath(path)
            painter_clear.fillPath(path, Qt.transparent)
        else:
            painter_clear.fillRect(shape_rect, Qt.transparent)
        painter_clear.end()

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

    without_shape_image.save(os.path.join(folder, "without_shape_area.png"))

    with open(os.path.join(folder, "shapes.json"), "w", encoding="utf-8") as f:
        json.dump({
            "background": original_image_path,
            "shapes": shape_data
        }, f, indent=4)

    print(f"✅ Сохранено {index - 1} фигур и итоговое изображение.")


