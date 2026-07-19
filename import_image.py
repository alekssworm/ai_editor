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
        if hasattr(self, "flow_direction_controller"):
            self.flow_direction_controller.reset()
        self.scene.clear()
        self.shape_registry.clear()
        self.shape_parents.clear()
        self.flow_directions.clear()
        self.shape_id_counter = 1
        self.ui.listWidget.clear()
        self.current_project_folder = None
        self.current_shapes_json_path = None
        if hasattr(self, "ai_window"):
            self.ai_window.reset_project_state()
        self.scene.addItem(pixmap_item)              # ✅ Добавляем именно этот объект
        self.ui.graphicsView.fitInView(self.scene.itemsBoundingRect(), Qt.KeepAspectRatio)
