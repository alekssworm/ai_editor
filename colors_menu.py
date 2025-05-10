from PySide6.QtGui import QBrush, QPen, QColor
from PySide6.QtWidgets import QColorDialog

def choose_color(self):
    color = QColorDialog.getColor()
    if color.isValid():
        # Обновляем цвет кнопок
        style = f"background-color: {color.name()};"
        self.ui.tools_Button.setStyleSheet(style)
        self.ui.palette_Button.setStyleSheet(style)

        # Создаём копию цвета с альфой
        transparent_color = QColor(color)
        transparent_color.setAlpha(50)

        # Применяем к выбранным фигурам
        selected_items = self.scene.selectedItems()
        for item in selected_items:
            item.setBrush(QBrush(transparent_color))

            pen = item.pen() if hasattr(item, "pen") else QPen()
            pen.setColor(color)  # Контур остаётся непрозрачным
            item.setPen(pen)

        # Сохраняем для новых фигур
        self.current_shape_color = transparent_color
        return color
    return None
