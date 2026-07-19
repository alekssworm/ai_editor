from PySide6.QtCore import Qt


def on_key_press(self, event):
    if event.key() != Qt.Key_Delete:
        return False

    from obj_list_logic import remove_shape_from_list

    for item in list(self.scene.selectedItems()):
        shape_id = next((sid for sid, obj in self.shape_registry.items() if obj == item), None)
        if shape_id is None:
            continue

        self.scene.removeItem(item)
        self.shape_registry.pop(shape_id, None)
        self.shape_parents.pop(shape_id, None)
        if hasattr(self, "flow_directions"):
            self.flow_directions.pop(shape_id, None)
        for child_id, parent_id in list(self.shape_parents.items()):
            if parent_id == shape_id:
                self.shape_parents[child_id] = None

        remove_shape_from_list(self.ui, shape_id)
        if hasattr(self, "ai_window"):
            self.ai_window.remove_shape_card(shape_id)

    return True
