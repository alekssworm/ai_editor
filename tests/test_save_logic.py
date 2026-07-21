from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QRectF
from PySide6.QtGui import QColor, QPixmap
from PySide6.QtWidgets import QApplication, QGraphicsPixmapItem

from draw_tools import ResizableRectItem
from save_logic import save_outputs


class SaveLogicTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def test_main_save_reuses_current_folder_and_writes_complete_project(self) -> None:
        from editor import MainWindow

        with tempfile.TemporaryDirectory() as directory:
            window = MainWindow()
            background_pixmap = QPixmap(64, 48)
            background_pixmap.fill(QColor("#204060"))
            background = QGraphicsPixmapItem(background_pixmap)
            window.scene.addItem(background)

            shape = ResizableRectItem(QRectF(4, 5, 24, 18), QColor("#00aaff"))
            window.scene.addItem(shape)
            window.shape_registry[1] = shape
            window.current_project_folder = directory

            with (
                patch("save_logic.QFileDialog.getExistingDirectory") as folder_dialog,
                patch("save_logic.QMessageBox.information") as information,
                patch("save_logic.QMessageBox.critical") as critical,
            ):
                result = save_outputs(window)

            project_path = Path(directory) / "shapes.json"
            self.assertEqual(result, str(project_path))
            self.assertTrue((Path(directory) / "background.png").is_file())
            self.assertTrue((Path(directory) / "without_shape_area.png").is_file())
            self.assertTrue((Path(directory) / "pieces" / "shape_1.png").is_file())
            self.assertFalse((Path(directory) / "shapes.json.tmp").exists())
            project = json.loads(project_path.read_text(encoding="utf-8"))
            self.assertEqual(project["shapes"][0]["id"], 1)
            folder_dialog.assert_not_called()
            information.assert_called_once()
            critical.assert_not_called()
            window.close()


if __name__ == "__main__":
    unittest.main()
