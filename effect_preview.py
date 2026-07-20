from __future__ import annotations

from pathlib import Path

from PIL import Image
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QCloseEvent, QImage, QPixmap, QResizeEvent
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)

from backend_async import run_in_thread
from effect_engine.preview import PreviewResult, build_project_preview


def _to_qimage(frame: Image.Image) -> QImage:
    rgb = frame.convert("RGB")
    raw = rgb.tobytes()
    return QImage(
        raw,
        rgb.width,
        rgb.height,
        rgb.width * 3,
        QImage.Format.Format_RGB888,
    ).copy()


class EffectPreviewDialog(QDialog):
    def __init__(self, result: PreviewResult, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle(f"Effect preview — shape {result.shape_id}")
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.resize(760, 560)

        self._frames = [_to_qimage(frame) for frame in result.frames]
        self._frame_index = 0
        self._playing = True

        self.preview_label = QLabel()
        self.preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_label.setMinimumSize(420, 280)
        self.preview_label.setStyleSheet("background: #151515; border: 1px solid #444;")

        self.status_label = QLabel(
            f"{result.effect_type}/{result.preset_id or 'default'} · "
            f"{len(result.frames)} frames · {result.fps} fps"
        )
        self.status_label.setToolTip(str(result.assets_dir))

        self.play_button = QPushButton("Pause")
        self.play_button.clicked.connect(self._toggle_playback)
        close_button = QPushButton("Close")
        close_button.clicked.connect(self.close)

        controls = QHBoxLayout()
        controls.addWidget(self.status_label)
        controls.addStretch(1)
        controls.addWidget(self.play_button)
        controls.addWidget(close_button)

        layout = QVBoxLayout(self)
        layout.addWidget(self.preview_label, 1)
        layout.addLayout(controls)

        self._timer = QTimer(self)
        self._timer.setInterval(max(1, round(1000 / result.fps)))
        self._timer.timeout.connect(self._next_frame)
        self._timer.start()
        self._show_current_frame()

    def _show_current_frame(self) -> None:
        if not self._frames:
            return
        pixmap = QPixmap.fromImage(self._frames[self._frame_index])
        self.preview_label.setPixmap(
            pixmap.scaled(
                self.preview_label.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        )

    def _next_frame(self) -> None:
        if not self._frames:
            return
        self._frame_index = (self._frame_index + 1) % len(self._frames)
        self._show_current_frame()

    def _toggle_playback(self) -> None:
        self._playing = not self._playing
        if self._playing:
            self._timer.start()
            self.play_button.setText("Pause")
        else:
            self._timer.stop()
            self.play_button.setText("Play")

    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)
        self._show_current_frame()

    def closeEvent(self, event: QCloseEvent) -> None:
        self._timer.stop()
        super().closeEvent(event)


def _selected_shape_id(window) -> int | None:
    selected = set(window.scene.selectedItems())
    for shape_id, item in window.shape_registry.items():
        if item in selected:
            return int(shape_id)
    return None


def start_effect_preview(window) -> None:
    if getattr(window, "_effect_preview_running", False):
        return

    project_path = getattr(window, "current_shapes_json_path", None)
    if not project_path or not Path(project_path).is_file():
        QMessageBox.information(
            window,
            "Preview",
            "Сначала сохраните или откройте проект.",
        )
        return

    shape_id = _selected_shape_id(window)
    if shape_id is None:
        QMessageBox.information(window, "Preview", "Выберите область на изображении.")
        return

    button = window.ui.preview_button
    original_text = button.text()
    window._effect_preview_running = True
    button.setEnabled(False)
    button.setText("preparing…")

    card_override = None
    ai_window = getattr(window, "ai_window", None)
    if ai_window is not None:
        for card in ai_window.collect_shape_cards_data():
            try:
                card_id = int(card.get("id", -1))
            except (AttributeError, TypeError, ValueError):
                continue
            if card_id == shape_id:
                card_override = card
                break
    direction_override = getattr(window, "flow_directions", {}).get(shape_id)

    def restore_button() -> None:
        window._effect_preview_running = False
        button.setEnabled(True)
        button.setText(original_text)

    def on_ready(result: PreviewResult) -> None:
        restore_button()
        previous = getattr(window, "_effect_preview_dialog", None)
        if previous is not None:
            try:
                previous.close()
            except RuntimeError:
                pass
        dialog = EffectPreviewDialog(result, window)
        window._effect_preview_dialog = dialog

        def clear_dialog_reference() -> None:
            if getattr(window, "_effect_preview_dialog", None) is dialog:
                window._effect_preview_dialog = None

        dialog.destroyed.connect(clear_dialog_reference)
        dialog.show()
        dialog.raise_()
        dialog.activateWindow()

    def on_error(message: str) -> None:
        restore_button()
        QMessageBox.critical(window, "Preview error", str(message))

    run_in_thread(
        window,
        build_project_preview,
        on_ready,
        on_error,
        project_path,
        shape_id,
        card_override=card_override,
        direction_override=direction_override,
        frame_count=18,
        fps=12,
        max_dimension=640,
        seed=shape_id,
    )
