from PySide6.QtGui import QBrush, QPen, QColor
from PySide6.QtWidgets import QColorDialog
from obj_list_logic import add_shape_to_list
from draw_tools import ResizableRectItem, SelectableCircleItem, SelectablePolygonItem

def choose_color(self):
    color = QColorDialog.getColor()
    if color.isValid():
        border_color = color.name()
        style = f"""
                QPushButton {{
                    background-color: #3c3c3c;
                    border-top:    1px solid {border_color};
                    border-left:   1px solid {border_color};
                    border-right:  1px solid {border_color};
                    border-bottom: 1px solid {border_color};
                    border-radius: 6px;
                    padding: 3px;
                }}
            """

        self.ui.palette_Button.setStyleSheet(style)

        # Создаём копию цвета с альфой
        transparent_color = QColor(color)
        transparent_color.setAlpha(50)

        # Применяем к выбранным фигурам
        selected_items = self.scene.selectedItems()
        for item in selected_items:
            if isinstance(item, (ResizableRectItem, SelectableCircleItem, SelectablePolygonItem)):
                item.setBrush(QBrush(transparent_color))

                pen = item.pen() if hasattr(item, "pen") else QPen()
                pen.setColor(color)  # Контур остаётся непрозрачным
                item.setPen(pen)
                shape_id = next((id_ for id_, obj in self.shape_registry.items() if obj is item), None)
                if shape_id is not None:
                    from obj_list_logic import update_shape_in_list
                    update_shape_in_list(self.ui, shape_id, color)

        # Сохраняем для новых фигур
        self.current_shape_color = transparent_color
        return color
    return None

