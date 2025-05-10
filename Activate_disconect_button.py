from PySide6.QtWidgets import QGraphicsScene



def activate_rectangle_mode(self):
    self.draw_controller.set_tool("rectangle")
    self.scene.mousePressEvent = self.draw_controller.mousePressEvent
    self.scene.mouseMoveEvent = self.draw_controller.mouseMoveEvent
    self.scene.mouseReleaseEvent = self.draw_controller.mouseReleaseEvent


def deactivate_drawing_mode(self):
    self.draw_controller.set_tool(None)
    # Убираем кастомные обработчики — отключаем рисование
    self.scene.mousePressEvent = QGraphicsScene.mousePressEvent.__get__(self.scene, QGraphicsScene)
    self.scene.mouseMoveEvent = QGraphicsScene.mouseMoveEvent.__get__(self.scene, QGraphicsScene)
    self.scene.mouseReleaseEvent = QGraphicsScene.mouseReleaseEvent.__get__(self.scene, QGraphicsScene)


def activate_circle_mode(self):
    self.draw_controller.set_tool("circle")
    self.scene.mousePressEvent = self.draw_controller.mousePressEvent
    self.scene.mouseMoveEvent = self.draw_controller.mouseMoveEvent
    self.scene.mouseReleaseEvent = self.draw_controller.mouseReleaseEvent