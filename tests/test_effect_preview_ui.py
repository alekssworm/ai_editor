from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import requests

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PIL import Image
from PySide6.QtCore import QEventLoop, QPointF, QRectF, Qt, QTimer
from PySide6.QtGui import QColor
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QPushButton

from draw_tools import ResizableRectItem
from effect_engine.preview import PreviewResult
from effect_preview import EffectPreviewDialog


class EffectPreviewDialogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def test_dialog_starts_and_cycles_frames(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            result = PreviewResult(
                frames=[
                    Image.new("RGB", (32, 24), "#102030"),
                    Image.new("RGB", (32, 24), "#405060"),
                ],
                assets_dir=Path(directory),
                effect_type="water",
                shape_id=8,
                fps=12,
                params={"strength": 4.0},
            )
            dialog = EffectPreviewDialog(result)

            self.assertTrue(dialog._timer.isActive())
            self.assertEqual(dialog._frame_index, 0)
            dialog._next_frame()
            self.assertEqual(dialog._frame_index, 1)
            dialog.close()
            self.assertFalse(dialog._timer.isActive())

    def test_main_window_constructs_with_preview_button(self) -> None:
        from editor import MainWindow

        window = MainWindow()
        self.assertEqual(window.ui.preview_button.text(), "Local preview")
        window.close()

    def test_ai_render_status_does_not_overwrite_selected_shape(self) -> None:
        from editor import MainWindow

        window = MainWindow()
        window.ai_window.add_shape_card(31, "Rectangle", "#00aaff")
        window.ai_window.select_shape_card(31)
        window.ai_window._set_render_status("AI render: checking")

        self.assertEqual(window.ai_window.selected_shape_id, 31)
        self.assertEqual(window.ai_window.ui.label_14.text(), "31")
        self.assertEqual(window.ai_window.ui.pushButton.text(), "AI render (WSL)")
        self.assertEqual(window.ai_window.statusBar().currentMessage(), "AI render: checking")
        window.close()

    def test_status_poll_stops_after_repeated_connection_errors(self) -> None:
        from editor import MainWindow

        window = MainWindow()
        panel = window.ai_window
        panel._svd_job_id = "job-offline"
        panel.ui.pushButton.setEnabled(False)
        panel._svd_timer.start(1000)

        with patch("ai_panel_logic.QMessageBox.warning") as warning:
            panel._on_svd_status_error("backend unavailable")
            panel._on_svd_status_error("backend unavailable")
            panel._on_svd_status_error("backend unavailable")

        self.assertIsNone(panel._svd_job_id)
        self.assertFalse(panel._svd_timer.isActive())
        self.assertTrue(panel.ui.pushButton.isEnabled())
        warning.assert_called_once()
        window.close()

    def test_offline_ai_render_restores_ui_with_short_message(self) -> None:
        import backend_client
        from editor import MainWindow

        with tempfile.TemporaryDirectory() as directory:
            project_path = Path(directory) / "shapes.json"
            project_path.write_text("{}", encoding="utf-8")
            window = MainWindow()
            panel = window.ai_window
            panel.add_shape_card(41, "Rectangle", "#00aaff")
            panel.select_shape_card(41)
            panel.set_render_sources(
                shapes_json_path=str(project_path),
                out_mp4_path=str(Path(directory) / "result.mp4"),
            )

            with (
                patch.object(
                    backend_client._session,
                    "request",
                    side_effect=requests.ConnectionError("raw pool details"),
                ),
                patch("ai_panel_logic.QMessageBox.warning") as warning,
            ):
                panel.on_render_clicked()
                loop = QEventLoop()
                thread = panel._backend_jobs[-1]["thread"]
                thread.finished.connect(loop.quit)
                if not thread.isRunning():
                    QTimer.singleShot(0, loop.quit)
                QTimer.singleShot(3000, loop.quit)
                loop.exec()
                self.app.processEvents()

            self.assertTrue(panel.ui.pushButton.isEnabled())
            self.assertEqual(panel.ui.label_14.text(), "41")
            self.assertIn("backend недоступен", panel.statusBar().currentMessage())
            shown_message = str(warning.call_args.args[2])
            self.assertIn("python -m uvicorn", shown_message)
            self.assertNotIn("raw pool details", shown_message)
            window.close()

    def test_preset_only_card_is_restored_and_serialized(self) -> None:
        from editor import MainWindow

        window = MainWindow()
        window.ai_window.add_shape_card(22, "Rectangle", "#00aaff")
        window.ai_window.restore_shape_cards_data(
            [
                {
                    "id": 22,
                    "tool_type": "water",
                    "preset_id": "still_water",
                    "main": None,
                    "sub": [],
                }
            ]
        )

        card = window.ai_window.collect_shape_cards_data()[0]
        self.assertEqual(card["preset_id"], "still_water")
        self.assertEqual(card["main"]["key"], "main_Still_water")
        window.close()

    def test_json_only_preset_is_added_to_water_panel(self) -> None:
        from editor import MainWindow
        from ui_water_tool import Ui_water_tool

        window = MainWindow()
        window.ai_window.add_shape_card(23, "Rectangle", "#00aaff")
        window.ai_window.select_shape_card(23)
        window.ai_window.load_tool_panel(Ui_water_tool)
        tool_widget = window.ai_window.tool_container_layout.itemAt(
            window.ai_window.tool_container_layout.count() - 1
        ).widget()
        button = tool_widget.findChild(QPushButton, "main_fast_river")

        self.assertIsNotNone(button)
        button.click()
        card = window.ai_window.collect_shape_cards_data()[0]
        self.assertEqual(card["preset_id"], "fast_river")
        self.assertEqual(card["main"]["params"]["intensity"], "default")
        window.close()

    def test_flow_direction_drag_is_normalized_and_stored(self) -> None:
        from editor import MainWindow

        window = MainWindow()
        window.resize(900, 650)
        window.show()
        window.scene.setSceneRect(0, 0, 200, 120)
        item = ResizableRectItem(QRectF(20, 20, 120, 60), QColor("#00aaff"))
        window.scene.addItem(item)
        window.shape_registry[12] = item
        window.ui.graphicsView.fitInView(
            window.scene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio
        )
        item.setSelected(True)
        self.app.processEvents()

        window.flow_direction_controller.activate()
        start = window.ui.graphicsView.mapFromScene(QPointF(40, 40))
        end = window.ui.graphicsView.mapFromScene(QPointF(110, 40))
        QTest.mousePress(
            window.ui.graphicsView.viewport(),
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier,
            start,
        )
        QTest.mouseMove(window.ui.graphicsView.viewport(), end, delay=5)
        QTest.mouseRelease(
            window.ui.graphicsView.viewport(),
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier,
            end,
        )
        self.app.processEvents()

        direction = window.flow_directions[12]
        self.assertAlmostEqual(direction[0], 1.0)
        self.assertAlmostEqual(direction[1], 0.0)
        self.assertFalse(window.flow_direction_controller.active)
        window.close()


if __name__ == "__main__":
    unittest.main()
