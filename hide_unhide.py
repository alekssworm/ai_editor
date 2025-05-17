from draw_tools import ResizableRectItem, SelectableCircleItem


def toggle_all_fill(self):
    self.fill_hidden_global = not self.fill_hidden_global
    for item in self.scene.items():
        if isinstance(item, (ResizableRectItem, SelectableCircleItem)):
            item.set_fill_visibility(self.fill_hidden_global)
