from PySide6.QtCore import QObject, QEvent

class MouseMoveFilter(QObject):
    def __init__(self, navigation_overlay, scene):
        super().__init__()
        self.navigation_overlay = navigation_overlay
        self.scene = scene

    def eventFilter(self, obj, event):
        if event.type() == QEvent.GraphicsSceneMouseMove:
            self.navigation_overlay.update_position(event.scenePos())
            print(f"🧭 Mouse at: {event.scenePos()}")

        return False
