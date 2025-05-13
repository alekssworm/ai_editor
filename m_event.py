from PySide6.QtCore import QObject, QEvent

class MouseMoveFilter(QObject):
    def __init__(self, navigation_overlay, scene):
        super().__init__()
        self.navigation_overlay = navigation_overlay
        self.scene = scene

    def eventFilter(self, source, event):
        if event.type() == QEvent.GraphicsSceneMouseMove:
            scene_pos = event.scenePos()
            label = self.navigation_overlay.ui.label
            label.setText(f"X:{int(scene_pos.x())}, Y:{int(scene_pos.y())} Object ID : 0 color:")
        return False
