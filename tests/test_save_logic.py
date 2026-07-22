from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QPointF, QRectF
from PySide6.QtGui import QColor, QImage, QPixmap, QPolygonF
from PySide6.QtWidgets import QApplication, QGraphicsPixmapItem

from draw_tools import ResizableRectItem, SelectablePolygonItem
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
            window.flow_directions[1] = (1.0, 0.0)
            window.flow_guides[1] = [
                {"start": [5.0, 10.0], "end": [25.0, 10.0]}
            ]
            window.effect_overrides[1] = {
                "speed_zones": [
                    {"center": [12.0, 14.0], "radius": 6.0, "value": 0.35}
                ]
            }
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
            self.assertFalse(list(Path(directory).rglob("*.tmp.png")))
            project = json.loads(project_path.read_text(encoding="utf-8"))
            self.assertEqual(project["shapes"][0]["id"], 1)
            self.assertEqual(project["flow_directions"]["1"], {"x": 1.0, "y": 0.0})
            self.assertEqual(
                project["flow_guides"]["1"],
                [
                    {
                        "start": [5.0, 10.0],
                        "control1": [11.666666666666668, 10.0],
                        "control2": [18.333333333333336, 10.0],
                        "end": [25.0, 10.0],
                    }
                ],
            )
            self.assertEqual(
                project["effect_overrides"]["1"]["speed_zones"],
                [{"center": [12.0, 14.0], "radius": 6.0, "value": 0.35}],
            )
            folder_dialog.assert_not_called()
            information.assert_called_once()
            critical.assert_not_called()
            window.close()

    def test_hidden_fill_does_not_change_saved_geometry_or_color(self) -> None:
        from editor import MainWindow

        with tempfile.TemporaryDirectory() as directory:
            window = MainWindow()
            background_pixmap = QPixmap(96, 72)
            background_pixmap.fill(QColor("#204060"))
            window.scene.addItem(QGraphicsPixmapItem(background_pixmap))
            shape = ResizableRectItem(
                QRectF(10, 12, 40, 20), QColor("#00aaff")
            )
            shape.set_fill_visibility(False)
            window.scene.addItem(shape)
            window.shape_registry[7] = shape
            window.shape_parents[7] = None

            with (
                patch("save_logic.QMessageBox.information"),
                patch("save_logic.QMessageBox.critical") as critical,
            ):
                result = save_outputs(window, directory)

            self.assertIsNotNone(result)
            critical.assert_not_called()

            project = json.loads(
                (Path(directory) / "shapes.json").read_text(encoding="utf-8")
            )
            saved = project["shapes"][0]
            self.assertEqual(
                (saved["x"], saved["y"], saved["width"], saved["height"]),
                (10, 12, 40, 20),
            )
            self.assertEqual(saved["color"], "#00aaff")
            window.close()

    def test_moved_polygon_piece_uses_scene_coordinates(self) -> None:
        from editor import MainWindow

        with tempfile.TemporaryDirectory() as directory:
            window = MainWindow()
            background_pixmap = QPixmap(120, 90)
            background_pixmap.fill(QColor("#407020"))
            window.scene.addItem(QGraphicsPixmapItem(background_pixmap))
            polygon = SelectablePolygonItem(
                QPolygonF(
                    [QPointF(10, 10), QPointF(40, 10), QPointF(10, 40)]
                ),
                QColor("#ff8800"),
            )
            polygon.setPos(45, 20)
            window.scene.addItem(polygon)
            window.shape_registry[8] = polygon
            window.shape_parents[8] = None

            with (
                patch("save_logic.QMessageBox.information"),
                patch("save_logic.QMessageBox.critical") as critical,
            ):
                result = save_outputs(window, directory)

            self.assertIsNotNone(result)
            critical.assert_not_called()

            project = json.loads(
                (Path(directory) / "shapes.json").read_text(encoding="utf-8")
            )
            points = project["shapes"][0]["points"]
            self.assertEqual(points[0], {"x": 55, "y": 30})
            piece = QImage(str(Path(directory) / "pieces" / "shape_8.png"))
            self.assertFalse(piece.isNull())
            self.assertTrue(
                any(
                    piece.pixelColor(x, y).alpha() > 0
                    for y in range(piece.height())
                    for x in range(piece.width())
                )
            )
            window.close()

    def test_current_geometry_recomputes_parent_relationships(self) -> None:
        from editor import MainWindow

        with tempfile.TemporaryDirectory() as directory:
            window = MainWindow()
            background_pixmap = QPixmap(120, 90)
            background_pixmap.fill(QColor("#405060"))
            window.scene.addItem(QGraphicsPixmapItem(background_pixmap))
            parent = ResizableRectItem(
                QRectF(10, 10, 80, 60), QColor("#00aaff")
            )
            child = ResizableRectItem(
                QRectF(25, 25, 15, 12), QColor("#ffaa00")
            )
            window.scene.addItem(parent)
            window.scene.addItem(child)
            window.shape_registry.update({1: parent, 2: child})
            window.shape_parents.update({1: None, 2: None})

            with (
                patch("save_logic.QMessageBox.information"),
                patch("save_logic.QMessageBox.critical") as critical,
            ):
                result = save_outputs(window, directory)

            self.assertIsNotNone(result)
            critical.assert_not_called()
            project = json.loads(
                (Path(directory) / "shapes.json").read_text(encoding="utf-8")
            )
            by_id = {shape["id"]: shape for shape in project["shapes"]}
            self.assertIsNone(by_id[1]["parent_id"])
            self.assertEqual(by_id[2]["parent_id"], 1)
            window.close()

    def test_rectangle_handle_tracks_programmatic_resize(self) -> None:
        shape = ResizableRectItem(QRectF(5, 5, 0, 0), QColor("#00aaff"))

        shape.setRect(QRectF(5, 5, 40, 20))

        self.assertEqual(shape.handles[0].pos(), shape.rect().bottomRight())


if __name__ == "__main__":
    unittest.main()
