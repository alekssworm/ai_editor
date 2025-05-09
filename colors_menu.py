from PySide6.QtWidgets import QColorDialog

def choose_color(self):
    color = QColorDialog.getColor()
    if color.isValid():
        # change color button
        style = f"background-color: {color.name()};"
        self.ui.tools_Button.setStyleSheet(style)
        self.ui.palette_Button.setStyleSheet(style)
        # -----
        return color
    return None
