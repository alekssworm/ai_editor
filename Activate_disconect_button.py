from PyQt6.QtWidgets import QGraphicsScene


def activate_rectangle_mode(self):
    self.draw_controller.set_tool("rectangle")
    self.scene.mousePressEvent = self.draw_controller.mousePressEvent
    self.scene.mouseMoveEvent = self.draw_controller.mouseMoveEvent
    self.scene.mouseReleaseEvent = self.draw_controller.mouseReleaseEvent


def deactivate_drawing_mode(self):
    self.draw_controller.set_tool(None)
    # Убираем кастомные обработчики — отключаем рисование
    self.scene.mousePressEvent = lambda event: QGraphicsScene.mousePressEvent(self.scene, event)
    self.scene.mouseMoveEvent = lambda event: QGraphicsScene.mouseMoveEvent(self.scene, event)
    self.scene.mouseReleaseEvent = lambda event: QGraphicsScene.mouseReleaseEvent(self.scene, event)


def activate_circle_mode(self):
    self.draw_controller.set_tool("circle")
    self.scene.mousePressEvent = self.draw_controller.mousePressEvent
    self.scene.mouseMoveEvent = self.draw_controller.mouseMoveEvent
    self.scene.mouseReleaseEvent = self.draw_controller.mouseReleaseEvent