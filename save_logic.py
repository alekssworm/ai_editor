import os
import json
from PySide6.QtWidgets import QFileDialog, QGraphicsPixmapItem
from PySide6.QtGui import QImage, QPainter, Qt, QPainterPath
from PySide6.QtCore import QPointF
from draw_tools import SelectableCircleItem, ResizableRectItem, ShapeItem
from draw_tools import SelectablePolygonItem

def save_outputs(self):
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

    parent_ids = [sid for sid, _ in parents]

    # Сначала сохраняем sub-объекты (children)
    for shape_id, item in children:
        shape_rect = item.sceneBoundingRect().toRect()
        brush_color = item.brush().color().name()

        if isinstance(item, SelectableCircleItem):
            item_type = "Circle"
            path = QPainterPath()
            path.addEllipse(0, 0, shape_rect.width(), shape_rect.height())
        elif isinstance(item, ResizableRectItem):
            item_type = "Rectangle"
            path = QPainterPath()
            path.addRect(0, 0, shape_rect.width(), shape_rect.height())
        elif isinstance(item, SelectablePolygonItem):
            item_type = "Polygon"
            polygon = item.polygon()
            path = QPainterPath()
            path.addPolygon(polygon.translated(-shape_rect.topLeft()))
        else:
            continue

        original_crop = original_image.copy(shape_rect)
        cut_image = QImage(shape_rect.size(), QImage.Format_ARGB32)
        cut_image.fill(Qt.transparent)

        cut_painter = QPainter(cut_image)
        cut_painter.drawImage(0, 0, original_crop)
        cut_painter.setCompositionMode(QPainter.CompositionMode_Clear)

        mask = QPainterPath()
        mask.addRect(0, 0, shape_rect.width(), shape_rect.height())
        mask = mask.subtracted(path)

        cut_painter.fillPath(mask, Qt.transparent)
        cut_painter.end()

        cut_image.save(os.path.join(folder, f"shape_{index}.png"))

        global_path = QPainterPath()
        if isinstance(item, SelectablePolygonItem):
            global_path.addPolygon(item.mapToScene(item.polygon()))
        else:
            global_path.addRect(shape_rect)

        for target in [without_shape_image, clean_parent_image]:
            painter_clear = QPainter(target)
            painter_clear.setCompositionMode(QPainter.CompositionMode_Clear)
            painter_clear.setClipPath(global_path)
            painter_clear.fillPath(global_path, Qt.transparent)
            painter_clear.end()

        if item_type == "Polygon":
            shape_data.append({
                "id": shape_id,
                "type": "Polygon",
                "points": [{"x": int(p.x()), "y": int(p.y())} for p in item.polygon()],
                "color": brush_color,
                "parent_id": self.shape_parents.get(shape_id)
            })
        else:
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

    # Затем сохраняем родителей (parents) — с вычитанием вложенных фигур
    for shape_id, item in parents:
        shape_rect = item.sceneBoundingRect().toRect()
        brush_color = item.brush().color().name()

        if isinstance(item, SelectableCircleItem):
            item_type = "Circle"
            path = QPainterPath()
            path.addEllipse(0, 0, shape_rect.width(), shape_rect.height())
        elif isinstance(item, ResizableRectItem):
            item_type = "Rectangle"
            path = QPainterPath()
            path.addRect(0, 0, shape_rect.width(), shape_rect.height())
        elif isinstance(item, SelectablePolygonItem):
            item_type = "Polygon"
            polygon = item.polygon()
            path = QPainterPath()
            path.addPolygon(polygon.translated(-shape_rect.topLeft()))
        else:
            continue

        original_crop = clean_parent_image.copy(shape_rect)
        cut_image = QImage(shape_rect.size(), QImage.Format_ARGB32)
        cut_image.fill(Qt.transparent)

        cut_painter = QPainter(cut_image)
        cut_painter.drawImage(0, 0, original_crop)
        cut_painter.setCompositionMode(QPainter.CompositionMode_Clear)

        mask = QPainterPath()
        mask.addRect(0, 0, shape_rect.width(), shape_rect.height())
        mask = mask.subtracted(path)

        for sid2, sub_item in self.shape_registry.items():
            if self.shape_parents.get(sid2) == shape_id:
                sub_path = QPainterPath()
                if isinstance(sub_item, SelectablePolygonItem):
                    translated_sub_polygon = sub_item.polygon().translated(
                        sub_item.scenePos() - item.scenePos()
                    )
                    sub_path.addPolygon(translated_sub_polygon)
                elif isinstance(sub_item, ResizableRectItem):
                    sub_rect = sub_item.sceneBoundingRect().translated(-shape_rect.topLeft())
                    sub_path.addRect(sub_rect)
                elif isinstance(sub_item, SelectableCircleItem):
                    sub_rect = sub_item.sceneBoundingRect().translated(-shape_rect.topLeft())
                    sub_path.addEllipse(sub_rect)
                mask = mask.subtracted(sub_path)

        cut_painter.fillPath(mask, Qt.transparent)
        cut_painter.end()

        cut_image.save(os.path.join(folder, f"shape_{index}.png"))

        global_path = QPainterPath()
        if isinstance(item, SelectablePolygonItem):
            global_path.addPolygon(item.mapToScene(item.polygon()))
        else:
            global_path.addRect(shape_rect)

        painter_clear = QPainter(without_shape_image)
        painter_clear.setCompositionMode(QPainter.CompositionMode_Clear)
        painter_clear.setClipPath(global_path)
        painter_clear.fillPath(global_path, Qt.transparent)
        painter_clear.end()

        if item_type == "Polygon":
            shape_data.append({
                "id": shape_id,
                "type": "Polygon",
                "points": [{"x": int(p.x()), "y": int(p.y())} for p in item.polygon()],
                "color": brush_color,
                "parent_id": self.shape_parents.get(shape_id)
            })
        else:
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