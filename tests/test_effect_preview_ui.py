from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

import requests

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PIL import Image
from PySide6.QtCore import QEventLoop, QPointF, QRectF, Qt, QTimer
from PySide6.QtGui import QColor
from PySide6.QtTest import QTest
from PySide6.QtWidgets import (
    QApplication,
    QDoubleSpinBox,
    QGraphicsScene,
    QPushButton,
)

from draw_tools import ResizableRectItem, SelectableCircleItem
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
                debug_maps={"Speed": Image.new("RGB", (32, 24), "red")},
            )
            dialog = EffectPreviewDialog(result)

            self.assertTrue(dialog._timer.isActive())
            self.assertEqual(dialog._frame_index, 0)
            self.assertEqual(dialog.map_selector.itemText(1), "Speed")
            dialog.map_selector.setCurrentText("Speed")
            self.assertFalse(dialog.play_button.isEnabled())
            dialog.map_selector.setCurrentText("Effect")
            dialog._next_frame()
            self.assertEqual(dialog._frame_index, 1)
            dialog.close()
            self.assertFalse(dialog._timer.isActive())

    def test_dialog_hq_export_uses_selected_mp4_path(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "final.mp4"
            callback = Mock(return_value=output)
            result = PreviewResult(
                frames=[Image.new("RGB", (16, 12), "blue") for _ in range(2)],
                assets_dir=Path(directory),
                effect_type="water",
                shape_id=2,
                fps=12,
                params={"strength": 2.0},
            )
            dialog = EffectPreviewDialog(result, export_callback=callback)

            def run_now(_owner, function, on_ok, _on_error, *args, **kwargs):
                on_ok(function(*args, **kwargs))

            with (
                patch(
                    "effect_preview.QFileDialog.getSaveFileName",
                    return_value=(str(output), "MP4 video (*.mp4)"),
                ),
                patch("effect_preview.run_in_thread", side_effect=run_now),
                patch("effect_preview.QMessageBox.information") as information,
            ):
                dialog._export_mp4()

            callback.assert_called_once_with(str(output))
            self.assertIn("Export complete", dialog.status_label.text())
            self.assertTrue(dialog.export_button.isEnabled())
            information.assert_called_once()
            dialog.close()

    def test_main_window_constructs_with_preview_button(self) -> None:
        from editor import MainWindow

        window = MainWindow()
        self.assertEqual(window.ui.preview_button.text(), "Local preview")
        self.assertEqual(window.ai_prepare_checkbox.text(), "AI prep")
        self.assertFalse(window.ai_prepare_checkbox.isChecked())
        self.assertEqual(window.ui.save_button.text(), "Save project")
        self.assertEqual(window.ai_window.ui.pushButton_9.text(), "Save effects")
        self.assertTrue(window.ai_window.ui.water_button.isEnabled())
        self.assertFalse(window.ai_window.ui.fire_button.isEnabled())
        self.assertFalse(window.ai_window.ui.light_button.isEnabled())
        self.assertTrue(window.ai_window.ui.weather_tool.isEnabled())
        window.close()

    def test_ai_render_status_does_not_overwrite_selected_shape(self) -> None:
        from editor import MainWindow

        window = MainWindow()
        window.ai_window.add_shape_card(31, "Rectangle", "#00aaff")
        window.ai_window.select_shape_card(31)
        window.ai_window._set_render_status("AI render: checking")

        self.assertEqual(window.ai_window.selected_shape_id, 31)
        self.assertEqual(window.ai_window.ui.label_14.text(), "31")
        self.assertEqual(window.ai_window.ui.pushButton.text(), "AI render")
        self.assertEqual(window.ai_window.statusBar().currentMessage(), "AI render: checking")
        window.close()

    def test_status_poll_keeps_job_for_reconnection_after_errors(self) -> None:
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

        self.assertEqual(panel._svd_job_id, "job-offline")
        self.assertTrue(panel._svd_timer.isActive())
        self.assertEqual(panel._svd_timer.interval(), 10000)
        self.assertTrue(panel.ui.pushButton.isEnabled())
        self.assertEqual(panel.ui.pushButton.text(), "Cancel render")
        warning.assert_not_called()
        window.close()

    def test_render_status_displays_denoising_progress(self) -> None:
        from editor import MainWindow

        window = MainWindow()
        panel = window.ai_window
        panel._handle_svd_status(
            {
                "state": "running",
                "progress": {"stage": "rendering", "step": 7, "steps": 25},
            }
        )

        self.assertIn("7/25", panel.statusBar().currentMessage())
        self.assertEqual(
            panel.render_status_label.text(),
            panel.statusBar().currentMessage(),
        )
        self.assertFalse(panel.render_progress_bar.isHidden())
        self.assertEqual(panel.render_progress_bar.value(), 7)
        window.close()

    def test_render_status_names_loop_interpolation(self) -> None:
        from editor import MainWindow

        window = MainWindow()
        window.ai_window._handle_svd_status(
            {
                "state": "running",
                "progress": {
                    "stage": "interpolating",
                    "current": 25,
                    "total": 72,
                },
            }
        )

        self.assertIn("сглаживание движения", window.ai_window.statusBar().currentMessage())
        window.close()

    def test_cancelled_render_restores_render_button(self) -> None:
        from editor import MainWindow

        window = MainWindow()
        panel = window.ai_window
        panel._svd_job_id = "cancelled-job"
        panel.ui.pushButton.setText("Cancelling...")

        panel._handle_svd_status({"state": "cancelled", "progress": {}})

        self.assertIsNone(panel._svd_job_id)
        self.assertTrue(panel.ui.pushButton.isEnabled())
        self.assertEqual(panel.ui.pushButton.text(), "AI render")
        window.close()

    def test_ai_render_syncs_current_project_before_submit(self) -> None:
        from editor import MainWindow

        with tempfile.TemporaryDirectory() as directory:
            project_path = Path(directory) / "shapes.json"
            project_path.write_text("{}", encoding="utf-8")
            window = MainWindow()
            panel = window.ai_window
            sync = Mock(return_value=str(project_path))
            panel.project_sync_callback = sync
            panel.render_masks_dir = directory
            panel.render_pieces_dir = directory
            panel.render_out_mp4_path = str(Path(directory) / "result.mp4")

            with patch.object(panel, "_start_remote_render") as start:
                panel.on_render_clicked()

            sync.assert_called_once_with()
            start.assert_called_once()
            self.assertEqual(start.call_args.args[0], str(project_path))
            window.close()

    def test_invalid_project_does_not_clear_current_scene(self) -> None:
        from editor import MainWindow
        from import_scene import load_scene

        with tempfile.TemporaryDirectory() as directory:
            project_path = Path(directory) / "broken.json"
            project_path.write_text(
                json.dumps({"background": "missing.png", "shapes": []}),
                encoding="utf-8",
            )
            window = MainWindow()
            existing = ResizableRectItem(QRectF(1, 2, 20, 10), QColor("#00aaff"))
            window.scene.addItem(existing)
            window.shape_registry[1] = existing

            with (
                patch(
                    "PySide6.QtWidgets.QFileDialog.getOpenFileName",
                    return_value=(str(project_path), "JSON (*.json)"),
                ),
                patch("PySide6.QtWidgets.QMessageBox.critical") as critical,
            ):
                load_scene(window)

            self.assertIs(window.shape_registry[1], existing)
            self.assertIs(existing.scene(), window.scene)
            critical.assert_called_once()
            window.close()

    def test_circle_drag_uses_euclidean_radius(self) -> None:
        from draw_logic import DrawingToolController

        scene = QGraphicsScene()
        controller = DrawingToolController(scene)
        controller.drawing = True
        controller.current_tool = "circle"
        controller.start_point = QPointF(10, 10)
        controller.current_item = SelectableCircleItem(
            QRectF(10, 10, 0, 0), QColor("#00aaff")
        )
        scene.addItem(controller.current_item)

        controller.mouseMoveEvent(
            SimpleNamespace(scenePos=lambda: QPointF(13, 14))
        )

        self.assertEqual(controller.current_item.rect().width(), 10.0)
        self.assertEqual(controller.current_item.rect().height(), 10.0)

    def test_ai_save_updates_only_effect_cards_atomically(self) -> None:
        from editor import MainWindow

        with tempfile.TemporaryDirectory() as directory:
            project_path = Path(directory) / "shapes.json"
            original = {
                "schema_version": 2,
                "background": "background.png",
                "shapes": [{"id": 22, "type": "Rectangle"}],
                "shape_cards": [],
                "flow_directions": {"22": [1.0, 0.0]},
                "custom_field": "preserve me",
            }
            project_path.write_text(
                json.dumps(original, ensure_ascii=False),
                encoding="utf-8",
            )

            window = MainWindow()
            panel = window.ai_window
            panel.add_shape_card(22, "Rectangle", "#00aaff")
            panel.restore_shape_cards_data(
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
            panel.set_render_sources(shapes_json_path=str(project_path))
            graphics_widget = panel.shape_cards[22]
            shape_card = graphics_widget.layout().itemAt(0).widget()
            shape_card.motion_controls.set_angle(90)

            with patch("ai_panel_logic.QMessageBox.information") as information:
                panel.ui.pushButton_9.click()

            saved = json.loads(project_path.read_text(encoding="utf-8"))
            self.assertEqual(saved["custom_field"], "preserve me")
            self.assertAlmostEqual(saved["flow_directions"]["22"]["x"], 0.0, places=6)
            self.assertAlmostEqual(saved["flow_directions"]["22"]["y"], 1.0, places=6)
            self.assertEqual(saved["shape_cards"][0]["id"], 22)
            self.assertEqual(saved["shape_cards"][0]["preset_id"], "still_water")
            self.assertEqual(saved["shape_cards"][0]["motion"]["angle_deg"], 90)
            self.assertFalse(list(Path(directory).glob(".shapes-*.tmp")))
            information.assert_called_once()
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
                patch.object(
                    backend_client,
                    "try_start_local_backend",
                    return_value=False,
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
            self.assertIn("backend не готов", panel.statusBar().currentMessage())
            shown_message = str(warning.call_args.args[2])
            self.assertIn("backend_server.py", shown_message)
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
        graphics_widget = window.ai_window.shape_cards[22]
        shape_card = graphics_widget.layout().itemAt(0).widget()
        self.assertEqual(shape_card.motion_controls.strength_spin.value(), 2)
        self.assertEqual(shape_card.motion_controls.cycles_spin.value(), 1)
        self.assertEqual(shape_card.motion_controls.strength_spin.maximum(), 4)
        self.assertEqual(shape_card.motion_controls.cycles_spin.maximum(), 2)
        window.close()

    def test_shape_card_position_round_trips_and_effect_can_be_reset(self) -> None:
        from editor import MainWindow

        window = MainWindow()
        panel = window.ai_window
        panel.add_shape_card(66, "Rectangle", "#00aaff")
        panel.restore_shape_cards_data(
            [
                {
                    "id": 66,
                    "tool_type": "water",
                    "preset_id": "river",
                    "panel_position": {"x": 175.5, "y": 82.0},
                    "main": None,
                    "sub": [],
                }
            ]
        )
        graphics_widget = panel.shape_cards[66]
        shape_card = graphics_widget.layout().itemAt(0).widget()

        saved = panel.collect_shape_cards_data()[0]
        self.assertEqual(saved["panel_position"], {"x": 175.5, "y": 82.0})
        self.assertIsNotNone(saved["main"])

        shape_card.clear_effects()
        reset = panel.collect_shape_cards_data()[0]
        self.assertIsNone(reset["tool_type"])
        self.assertIsNone(reset["main"])
        self.assertEqual(reset["sub"], [])
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

    def test_rain_panel_is_built_from_json_parameter_schema(self) -> None:
        from editor import MainWindow
        from ui_weather_tool import Ui_weather_tool

        window = MainWindow()
        panel = window.ai_window
        panel.add_shape_card(24, "Rectangle", "#00aaff")
        panel.select_shape_card(24)
        panel.load_tool_panel(Ui_weather_tool)
        tool_widget = panel.tool_container_layout.itemAt(
            panel.tool_container_layout.count() - 1
        ).widget()
        button = tool_widget.findChild(QPushButton, "main_Rain")

        self.assertIsNotNone(button)
        self.assertTrue(button.isVisibleTo(tool_widget))
        button.click()
        graphics_widget = panel.shape_cards[24]
        shape_card = graphics_widget.layout().itemAt(0).widget()
        density = shape_card.findChild(QDoubleSpinBox)
        self.assertIsNotNone(density)
        self.assertEqual(density.property("parameter_id"), "density")
        density.setValue(0.82)

        card = panel.collect_shape_cards_data()[0]
        self.assertEqual(card["tool_type"], "rain")
        self.assertEqual(card["preset_id"], "rain")
        self.assertEqual(card["main"]["params"]["density"], 0.82)
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
        self.assertEqual(len(window.flow_guides[12]), 1)
        guide = window.flow_guides[12][0]
        self.assertAlmostEqual(guide["start"][0], 40.0, delta=0.2)
        self.assertAlmostEqual(guide["start"][1], 40.0, delta=0.2)
        self.assertAlmostEqual(guide["end"][0], 110.0, delta=0.2)
        self.assertAlmostEqual(guide["end"][1], 40.0, delta=0.2)
        self.assertTrue(window.flow_direction_controller.active)

        second_start = window.ui.graphicsView.mapFromScene(QPointF(70, 30))
        second_end = window.ui.graphicsView.mapFromScene(QPointF(70, 70))
        QTest.mousePress(
            window.ui.graphicsView.viewport(),
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.ShiftModifier,
            second_start,
        )
        QTest.mouseMove(window.ui.graphicsView.viewport(), second_end, delay=5)
        QTest.mouseRelease(
            window.ui.graphicsView.viewport(),
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.ShiftModifier,
            second_end,
        )
        self.app.processEvents()

        self.assertEqual(len(window.flow_guides[12]), 2)
        self.assertGreater(window.flow_directions[12][1], 0.0)

        zone_start = window.ui.graphicsView.mapFromScene(QPointF(75, 45))
        zone_end = window.ui.graphicsView.mapFromScene(QPointF(95, 45))
        QTest.mousePress(
            window.ui.graphicsView.viewport(),
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.ControlModifier,
            zone_start,
        )
        QTest.mouseMove(window.ui.graphicsView.viewport(), zone_end, delay=5)
        QTest.mouseRelease(
            window.ui.graphicsView.viewport(),
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.ControlModifier,
            zone_end,
        )
        self.app.processEvents()

        fast_zone = window.effect_overrides[12]["speed_zones"][0]
        self.assertEqual(fast_zone["value"], 1.5)
        self.assertAlmostEqual(fast_zone["radius"], 20.0, delta=0.3)
        QTest.keyClick(window.ui.graphicsView.viewport(), Qt.Key.Key_Delete)
        self.app.processEvents()
        self.assertNotIn(12, window.flow_guides)
        self.assertNotIn(12, window.effect_overrides)
        window.flow_direction_controller.cancel()
        self.assertFalse(window.flow_direction_controller.active)
        window.close()

    def test_ai_motion_controls_update_main_flow_and_round_trip(self) -> None:
        from editor import MainWindow

        window = MainWindow()
        item = ResizableRectItem(QRectF(10, 10, 80, 40), QColor("#00aaff"))
        window.scene.addItem(item)
        window.shape_registry[55] = item
        window.ai_window.add_shape_card(55, "Rectangle", "#00aaff")
        graphics_widget = window.ai_window.shape_cards[55]
        shape_card = graphics_widget.layout().itemAt(0).widget()

        shape_card.motion_controls.set_angle(90)
        shape_card.motion_controls.strength_spin.setValue(11)
        shape_card.motion_controls.cycles_spin.setValue(3)
        self.app.processEvents()

        direction = window.flow_directions[55]
        self.assertAlmostEqual(direction[0], 0.0, places=6)
        self.assertAlmostEqual(direction[1], 1.0, places=6)
        saved = window.ai_window.collect_shape_cards_data()[0]["motion"]
        self.assertEqual(saved["angle_deg"], 90)
        self.assertEqual(saved["strength"], 11)
        self.assertEqual(saved["cycles"], 3)
        window.close()


if __name__ == "__main__":
    unittest.main()
