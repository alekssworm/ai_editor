from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QFileDialog, QGraphicsPixmapItem

def import_image(self):
    file_path, _ = QFileDialog.getOpenFileName(
        self, "Выберите изображение", "", "Изображения (*.png *.jpg *.bmp *.jpeg *.gif)"
    )
    if file_path:
        pixmap = QPixmap(file_path)
        pixmap_item = QGraphicsPixmapItem(pixmap)
        pixmap_item.setData(Qt.UserRole, file_path)  # ✅ Сохраняем путь
        self.scene.clear()
        self.scene.addItem(pixmap_item)              # ✅ Добавляем именно этот объект
        self.ui.graphicsView.fitInView(self.scene.itemsBoundingRect(), Qt.KeepAspectRatio)
