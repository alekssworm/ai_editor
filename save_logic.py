from PySide6.QtCore import QPointF
from PySide6.QtGui import QImage, QPainter, Qt, QPixmap, QPainterPath
from PySide6.QtWidgets import QGraphicsItem, QGraphicsPixmapItem
from PySide6.QtGui import QPainterPath



def save_outputs(self):
    rect = self.scene.sceneRect()
    size = rect.size().toSize()

    # Найти фон
    background = None
    for item in self.scene.items():
        if isinstance(item, QGraphicsPixmapItem):
            background = item
            break

    if not background:
        print("❌ Фон не найден.")
        return

    # Найти первую фигуру (ограничим пока одним)
    shape_item = None
    for item in self.scene.items():
        if isinstance(item, QGraphicsItem) and not isinstance(item, QGraphicsPixmapItem):
            shape_item = item
            break

    if shape_item is None:
        print("❌ Фигура не найдена.")
        return

    shape_rect = shape_item.sceneBoundingRect().toRect()

    # 1️⃣ Сцена полностью (включая фигуру)
    full_with_shape = QImage(size, QImage.Format_ARGB32)
    full_with_shape.fill(Qt.transparent)

    painter = QPainter(full_with_shape)
    self.scene.render(painter)
    painter.end()

    # 2️⃣ Вырезаем фигуру из уже нарисованного изображения
    painter = QPainter(full_with_shape)

    # определяем форму
    painter.setCompositionMode(QPainter.CompositionMode_Clear)

    from draw_tools import SelectableCircleItem  # Импорт для isinstance()

    if isinstance(shape_item, SelectableCircleItem):
        path = QPainterPath()
        path.addEllipse(shape_item.sceneBoundingRect())
        painter.setClipPath(path)
        painter.fillPath(path, Qt.transparent)
    else:
        painter.fillRect(shape_item.sceneBoundingRect(), Qt.transparent)

    painter.end()

    full_with_shape.save("image_without_shape_area.png")



    # 3️⃣ Вырезаем только форму (например, круг)
    cut_size = shape_rect.size()
    cut_image = QImage(cut_size, QImage.Format_ARGB32)
    cut_image.fill(Qt.transparent)

    painter = QPainter(cut_image)

    # Сдвигаем фон так, чтобы нужная область попала в (0, 0)
    source_rect = shape_rect
    target_point = QPointF(-source_rect.x(), -source_rect.y())
    original_image = background.pixmap().toImage()
    painter.drawImage(target_point, original_image)

    if isinstance(shape_item, SelectableCircleItem):
        path = QPainterPath()
        path.addRect(0, 0, cut_size.width(), cut_size.height())  # всё изображение
        circle = QPainterPath()
        circle.addEllipse(0, 0, cut_size.width(), cut_size.height())
        path = path.subtracted(circle)  # вычитаем круг — получаем всё КРОМЕ него

        painter.setCompositionMode(QPainter.CompositionMode_Clear)
        painter.fillPath(path, Qt.transparent)

    painter.end()
    cut_image.save("shape_only_area.png")

    print("✅ Сохранено:")
    print("🟢 image_without_shape_area.png (фон + фигуры с вырезом)")
    print("🟢 shape_only_area.png (только область под фигурой)")
