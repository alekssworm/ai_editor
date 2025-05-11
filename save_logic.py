from PySide6.QtWidgets import QFileDialog, QGraphicsPixmapItem, QGraphicsItem
from PySide6.QtGui import QImage, QPainter, Qt, QPainterPath
from PySide6.QtCore import QPointF
from draw_tools import SelectableCircleItem, ResizableRectItem
import json
import os

def save_outputs(self):
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

    original_image = background.pixmap().toImage()

    # 1️⃣ Фоновое изображение + фигуры
    full_scene = QImage(size, QImage.Format_ARGB32)
    full_scene.fill(Qt.transparent)
    painter = QPainter(full_scene)
    self.scene.render(painter)
    painter.end()

    # 2️⃣ Копия — будем вырезать все фигуры
    image_without_shapes = QImage(full_scene)
    painter = QPainter(image_without_shapes)
    painter.setCompositionMode(QPainter.CompositionMode_Clear)

    shape_data = []
    index = 1

    from draw_tools import ShapeItem

    for item in reversed(self.scene.items()):
        if not isinstance(item, ShapeItem):
            continue



        shape_rect = item.sceneBoundingRect().toRect()
        brush_color = item.brush().color().name()
        item_type = "Circle" if isinstance(item, SelectableCircleItem) else "Rectangle"

        # ---- вырез из общей сцены
        if item_type == "Circle":
            path = QPainterPath()
            path.addEllipse(shape_rect)
            painter.setClipPath(path)
            painter.fillPath(path, Qt.transparent)
        else:
            painter.fillRect(shape_rect, Qt.transparent)

        # ---- вырез в отдельный файл
        cut_size = shape_rect.size()
        cut_image = QImage(cut_size, QImage.Format_ARGB32)
        cut_image.fill(Qt.transparent)

        cut_painter = QPainter(cut_image)
        offset = QPointF(-shape_rect.x(), -shape_rect.y())
        cut_painter.drawImage(offset, original_image)

        if item_type == "Circle":
            path = QPainterPath()
            path.addRect(0, 0, cut_size.width(), cut_size.height())
            circle = QPainterPath()
            circle.addEllipse(0, 0, cut_size.width(), cut_size.height())
            mask = path.subtracted(circle)
            cut_painter.setCompositionMode(QPainter.CompositionMode_Clear)
            cut_painter.fillPath(mask, Qt.transparent)

        cut_painter.end()

        cut_path = os.path.join(folder, f"shape_{index}.png")
        cut_image.save(cut_path)
        index += 1

        shape_data.append({
            "type": item_type,
            "x": int(shape_rect.x()),
            "y": int(shape_rect.y()),
            "width": int(shape_rect.width()),
            "height": int(shape_rect.height()),
            "color": brush_color
        })

    painter.end()

    # 3️⃣ Сохраняем итог
    image_without_shapes.save(os.path.join(folder, "image_without_shape_area.png"))

    with open(os.path.join(folder, "shapes.json"), "w", encoding="utf-8") as f:
        json.dump(shape_data, f, indent=4)

    print(f"✅ Сохранено {index - 1} фигур.")

