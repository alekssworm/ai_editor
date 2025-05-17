from PySide6.QtWidgets import QListWidgetItem
from PySide6.QtGui import QPixmap, QIcon, QColor

def add_shape_to_list(ui, shape_id: int, color: QColor):
    """Добавляет элемент в listWidget: ID: 1 | color: 🟥 (цветной квадрат справа от текста)"""

    # Генерируем текст
    text = f"ID: {shape_id} "

    # Создаём иконку: просто цветной квадрат
    pixmap = QPixmap(12, 12)
    pixmap.fill(QColor(color))
    icon = QIcon(pixmap)

    # Создаём item с текстом и иконкой
    item = QListWidgetItem(text)
    item.setIcon(icon)

    ui.listWidget.addItem(item)

def on_list_item_selected(self, item):
    text = item.text()
    try:
        shape_id = int(text.split("ID:")[1].strip())
    except (IndexError, ValueError):
        return

    shape = self.shape_registry.get(shape_id)
    if shape:
        # Снять выделение со всех
        for obj in self.scene.selectedItems():
            obj.setSelected(False)

        shape.setSelected(True)

        self.ui.graphicsView.centerOn(shape)
        self.ui.listWidget.setCurrentItem(item)  # 🔷 Подсветка
        from on_shape_selected import on_shape_selected
        on_shape_selected(self)  # 🔷 Обновление описания


def update_shape_in_list(ui, shape_id: int, color: QColor):
    """Обновляет цвет у уже существующего shape_id в списке"""
    for i in range(ui.listWidget.count()):
        item = ui.listWidget.item(i)
        if f"ID: {shape_id}" in item.text():
            pixmap = QPixmap(12, 12)
            pixmap.fill(QColor(color))
            icon = QIcon(pixmap)
            item.setIcon(icon)
            break

