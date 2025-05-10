from PySide6.QtGui import QColor
from draw_tools import SelectableRectItem, SelectableCircleItem

def on_shape_selected(self):
    selected_items = self.scene.selectedItems()
    if not selected_items:
        self.ui.comboBox_3.clear()
        return

    item = selected_items[0]
    shape_id = None

    for id_, obj in self.shape_registry.items():
        if obj is item:
            shape_id = id_
            break

    # Определение типа фигуры
    if isinstance(item, SelectableRectItem):
        shape_type = "Rectangle"
    elif isinstance(item, SelectableCircleItem):
        shape_type = "Circle"
    else:
        shape_type = "Unknown"

    # Цвет
    color = item.brush().color() if item.brush() else None
    color_name = color.name() if color else "no color"

    # Позиция
    rect = item.sceneBoundingRect()
    pos_str = f"({int(rect.x())}, {int(rect.y())})"

    # Обновить comboBox
    self.ui.comboBox_3.clear()
    self.ui.comboBox_3.addItem(f"ID: {shape_id} | Type: {shape_type} | Color: {color_name} | Pos: {pos_str}")
