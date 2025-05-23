from draw_tools import ResizableRectItem, SelectableCircleItem ,SelectablePolygonItem


def toggle_all_fill(self):
    self.fill_hidden_global = not self.fill_hidden_global
    for item in self.scene.items():
        if isinstance(item, (ResizableRectItem, SelectableCircleItem,SelectablePolygonItem)):
            item.set_fill_visibility(self.fill_hidden_global)
