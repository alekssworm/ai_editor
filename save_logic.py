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

    for group in [children, parents]:
        for shape_id, item in group:
            shape_rect = item.sceneBoundingRect().toRect()
            brush_color = item.brush().color().name()

            if isinstance(item, SelectableCircleItem):
                item_type = "Circle"
            elif isinstance(item, ResizableRectItem):
                item_type = "Rectangle"
            elif isinstance(item, SelectablePolygonItem):
                item_type = "Polygon"
            else:
                continue

            if item_type == "Polygon":
                # Глобальный путь (для вырезания из общего изображения)
                scene_polygon = item.mapToScene(item.polygon())
                polygon_path = QPainterPath()
                polygon_path.addPolygon(scene_polygon)

                # Локальный путь (для cut_image)
                shape_rect = item.sceneBoundingRect().toRect()
                translated_polygon = item.polygon().translated(-shape_rect.topLeft())
                translated_path = QPainterPath()
                translated_path.addPolygon(translated_polygon)

                # Вырезаем из original_image по shape_rect
                original_crop = original_image.copy(shape_rect)
                cut_image = QImage(shape_rect.size(), QImage.Format_ARGB32)
                cut_image.fill(Qt.transparent)

                cut_painter = QPainter(cut_image)
                cut_painter.drawImage(0, 0, original_crop)
                cut_painter.setCompositionMode(QPainter.CompositionMode_Clear)

                mask = QPainterPath()
                mask.addRect(0, 0, shape_rect.width(), shape_rect.height())
                mask = mask.subtracted(translated_path)
                cut_painter.fillPath(mask, Qt.transparent)
                cut_painter.end()

                cut_image.save(os.path.join(folder, f"shape_{index}.png"))

                # Вырезаем из сцены
                for target in [without_shape_image, clean_parent_image]:
                    painter_clear = QPainter(target)
                    painter_clear.setCompositionMode(QPainter.CompositionMode_Clear)

                    sub_path = QPainterPath()
                    sub_path.addPath(polygon_path)

                    for sid2, sub_item in self.shape_registry.items():
                        if self.shape_parents.get(sid2) == shape_id and isinstance(sub_item, SelectablePolygonItem):
                            sub_poly = sub_item.mapToScene(sub_item.polygon())
                            sub_p = QPainterPath()
                            sub_p.addPolygon(sub_poly)
                            sub_path = sub_path.subtracted(sub_p)

                    painter_clear.setClipPath(sub_path)
                    painter_clear.fillPath(sub_path, Qt.transparent)
                    painter_clear.end()

                # JSON
                shape_data.append({
                    "id": shape_id,
                    "type": "Polygon",
                    "points": [{"x": int(p.x()), "y": int(p.y())} for p in item.polygon()],
                    "color": brush_color,
                    "parent_id": self.shape_parents.get(shape_id)
                })

                index += 1
                continue

            cut_size = shape_rect.size()
            cut_image = QImage(cut_size, QImage.Format_ARGB32)
            cut_image.fill(Qt.transparent)
            cut_painter = QPainter(cut_image)
            cut_painter.setPen(Qt.NoPen)
            offset = QPointF(-shape_rect.x(), -shape_rect.y())
            cut_painter.drawImage(offset, clean_parent_image if group is parents else original_image)

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

    without_shape_image.save(os.path.join(folder, "without_shape_area.png"))

    with open(os.path.join(folder, "shapes.json"), "w", encoding="utf-8") as f:
        json.dump({
            "background": original_image_path,
            "shapes": shape_data
        }, f, indent=4)

    print(f"✅ Сохранено {index - 1} фигур и итоговое изображение.")


