from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QFileDialog, QGraphicsPixmapItem



def import_image(self):
    file_path, _ = QFileDialog.getOpenFileName(
        self, "Выберите изображение", "", "Изображения (*.png *.jpg *.bmp *.jpeg *.gif)"
    )
    if file_path:
        pixmap = QPixmap(file_path)
        self.scene.clear()
        self.scene.addItem(QGraphicsPixmapItem(pixmap))
        self.ui.graphicsView.fitInView(self.scene.itemsBoundingRect(), Qt.KeepAspectRatio)