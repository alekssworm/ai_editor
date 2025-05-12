from PySide6.QtWidgets import QGraphicsScene
from PySide6.QtGui import QColor


def highlight_tool(self, active_button):
    buttons = [
        self.ui.Cursor,
        self.ui.Rectangle,
        self.ui.Circle
    ]

    # Получаем текущий цвет из self.current_shape_color (из colors_menu)
    if hasattr(self, "current_shape_color") and isinstance(self.current_shape_color, QColor):
        use_custom_color = True
        border_color = self.current_shape_color.name()
    else:
        use_custom_color = False

    for button in buttons:
        if button == active_button:
            if use_custom_color:
                # Полноцветная обводка
                style = f"""
                    QPushButton {{
                        background-color: #3c3c3c;
                        border: 1px solid {border_color};
                        border-radius: 6px;
                        padding: 3px;
                    }}
                """
            else:
                # Классический стиль обводки
                style = """
                    QPushButton {
                        background-color: #444444;
                        border-top:    1px solid #D3D3D3;
                        border-left:   1px solid #D3D3D3;
                        border-right:  1px solid #D3D3D3;
                        border-bottom: 1px solid #FFFFFF;
                        border-radius: 6px;
                        padding: 3px;
                    }
                """
            button.setStyleSheet(style)

        else:
            # Сбросить стиль для неактивных
            button.setStyleSheet("""
                QPushButton {
                    background-color: #3c3c3c;
                    border-top:    1px solid #4a4a4a;
                    border-left:   1px solid #4a4a4a;
                    border-right:  1px solid #4a4a4a;
                    border-bottom: 1px solid #5b5b5b;
                    border-radius: 6px;
                    padding: 3px;
                }
            """)




def activate_rectangle_mode(self):
    self.draw_controller.set_tool("rectangle")
    self.scene.mousePressEvent = self.draw_controller.mousePressEvent
    self.scene.mouseMoveEvent = self.draw_controller.mouseMoveEvent
    self.scene.mouseReleaseEvent = self.draw_controller.mouseReleaseEvent
    highlight_tool(self, self.ui.Rectangle)





def activate_circle_mode(self):
    self.draw_controller.set_tool("circle")
    self.scene.mousePressEvent = self.draw_controller.mousePressEvent
    self.scene.mouseMoveEvent = self.draw_controller.mouseMoveEvent
    self.scene.mouseReleaseEvent = self.draw_controller.mouseReleaseEvent
    highlight_tool(self, self.ui.Circle)


def deactivate_drawing_mode(self):
    self.draw_controller.set_tool(None)

    def default_mouse_press(event):
        QGraphicsScene.mousePressEvent(self.scene, event)

    def default_mouse_move(event):
        QGraphicsScene.mouseMoveEvent(self.scene, event)

    def default_mouse_release(event):
        QGraphicsScene.mouseReleaseEvent(self.scene, event)

    self.scene.mousePressEvent = default_mouse_press
    self.scene.mouseMoveEvent = default_mouse_move
    self.scene.mouseReleaseEvent = default_mouse_release

    highlight_tool(self, self.ui.Cursor)