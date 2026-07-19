from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PIL import Image
from PySide6.QtWidgets import QApplication

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
        self.assertEqual(window.ui.preview_button.text(), "preview")
        window.close()


if __name__ == "__main__":
    unittest.main()
