from draw_tools import ResizableRectItem


def show_all_handles(self):
    if not hasattr(self, "handles_visible"):
        self.handles_visible = False

    self.handles_visible = not self.handles_visible

    for item in self.scene.items():
        if isinstance(item, ResizableRectItem):
            if self.handles_visible:
                item.show_handles()
            else:
                item.hide_handles()
