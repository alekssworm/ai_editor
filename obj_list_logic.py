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
