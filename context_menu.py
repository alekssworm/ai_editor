from PySide6.QtCore import Qt


def on_key_press(self, event):
    if event.key() == Qt.Key_Delete:
        for item in self.scene.selectedItems():
            self.scene.removeItem(item)
            for sid, obj in list(self.shape_registry.items()):
                if obj == item:
                    del self.shape_registry[sid]
                    break
