from __future__ import annotations

from pathlib import Path
from typing import Callable

from PIL import Image
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QCloseEvent, QImage, QPainter, QPixmap, QResizeEvent
from PySide6.QtWidgets import (
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QComboBox,
    QSlider,
    QVBoxLayout,
)

from backend_async import run_in_thread
from effect_engine.preview import (
    PreviewResult,
    build_project_preview,
    export_project_loop,
)


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
    def __init__(
        self,
        result: PreviewResult,
        parent=None,
        *,
        export_callback: Callable[[str], Path] | None = None,
        default_export_path: str | Path | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(f"Effect preview — shape {result.shape_id}")
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.resize(760, 560)

        self._frames = [_to_qimage(frame) for frame in result.frames]
        self._debug_maps = {
            name: _to_qimage(image) for name, image in result.debug_maps.items()
        }
        mask_map = self._debug_maps.get("Mask")
        if mask_map is not None:
            alpha = mask_map.convertToFormat(QImage.Format.Format_Grayscale8)
            for name, debug_map in tuple(self._debug_maps.items()):
                overlay = debug_map.convertToFormat(QImage.Format.Format_ARGB32)
                overlay.setAlphaChannel(alpha)
                self._debug_maps[name] = overlay
        self._frame_index = 0
        self._playing = True
        self._export_callback = export_callback
        self._default_export_path = str(default_export_path or "effect_loop.mp4")
        self._export_running = False
        self.shape_id = int(result.shape_id)

        self.preview_label = QLabel()
        self.preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_label.setMinimumSize(420, 280)
        self.preview_label.setStyleSheet("background: #151515; border: 1px solid #444;")

        status = (
            f"{result.effect_type}/{result.preset_id or 'default'} · "
            f"{len(result.frames)} frames · {result.fps} fps"
        )
        if result.warnings:
            status += " · AI fallback"
        if result.provider_states:
            status += " · " + " · ".join(
                f"{name.title()}: {state.get('mode', 'unknown')}"
                for name, state in result.provider_states.items()
            )
        self.status_label = QLabel(status)
        tooltip = str(result.assets_dir)
        if result.warnings:
            tooltip += "\n\nAI fallback:\n" + "\n".join(result.warnings)
        self.status_label.setToolTip(tooltip)

        self.play_button = QPushButton("Pause")
        self.play_button.clicked.connect(self._toggle_playback)
        self.map_selector = QComboBox()
        self.map_selector.addItem("Effect")
        self.map_selector.addItems(list(self._debug_maps))
        self.map_selector.setToolTip(
            "Inspect prepared maps before deterministic rendering"
        )
        self.map_selector.currentTextChanged.connect(self._show_current_frame)
        self.overlay_opacity = QSlider(Qt.Orientation.Horizontal)
        self.overlay_opacity.setRange(0, 100)
        self.overlay_opacity.setValue(72)
        self.overlay_opacity.setFixedWidth(90)
        self.overlay_opacity.setToolTip("Prepared map overlay opacity")
        self.overlay_opacity.valueChanged.connect(self._show_current_frame)
        self.export_button = QPushButton("Export MP4 (24 fps)")
        self.export_button.setToolTip(
            "Full-resolution deterministic export: 72 frames, H.264 CRF 18"
        )
        self.export_button.clicked.connect(self._export_mp4)
        self.export_button.setVisible(export_callback is not None)
        close_button = QPushButton("Close")
        close_button.clicked.connect(self.close)

        controls = QHBoxLayout()
        controls.addWidget(self.status_label)
        controls.addWidget(self.map_selector)
        controls.addWidget(QLabel("Overlay"))
        controls.addWidget(self.overlay_opacity)
        controls.addStretch(1)
        controls.addWidget(self.export_button)
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
        selected_map = self.map_selector.currentText()
        if selected_map != "Effect" and selected_map in self._debug_maps:
            if self._frames:
                image = self._frames[self._frame_index].copy()
                painter = QPainter(image)
                painter.setOpacity(self.overlay_opacity.value() / 100.0)
                painter.drawImage(0, 0, self._debug_maps[selected_map])
                painter.end()
                self.play_button.setEnabled(True)
            else:
                image = self._debug_maps[selected_map]
                self.play_button.setEnabled(False)
            self.overlay_opacity.setEnabled(True)
        elif self._frames:
            image = self._frames[self._frame_index]
            self.play_button.setEnabled(True)
            self.overlay_opacity.setEnabled(False)
        else:
            return
        pixmap = QPixmap.fromImage(image)
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

    def _export_mp4(self) -> None:
        if self._export_callback is None or self._export_running:
            return
        output_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export deterministic loop",
            self._default_export_path,
            "MP4 video (*.mp4)",
        )
        if not output_path:
            return
        if not output_path.lower().endswith(".mp4"):
            output_path += ".mp4"

        self._export_running = True
        self.export_button.setEnabled(False)
        self.export_button.setText("Exporting 72 frames...")
        self.status_label.setText("Rendering full-resolution deterministic loop...")

        def on_ready(result_path: Path) -> None:
            self._export_running = False
            self.export_button.setEnabled(True)
            self.export_button.setText("Export MP4 (24 fps)")
            self.status_label.setText(f"Export complete: {result_path}")
            QMessageBox.information(
                self,
                "Export complete",
                f"Video saved:\n{result_path}",
            )

        def on_error(message: str) -> None:
            self._export_running = False
            self.export_button.setEnabled(True)
            self.export_button.setText("Export MP4 (24 fps)")
            self.status_label.setText("Export failed")
            QMessageBox.critical(self, "Export error", str(message))

        run_in_thread(
            self,
            self._export_callback,
            on_ready,
            on_error,
            output_path,
        )

    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)
        self._show_current_frame()

    def closeEvent(self, event: QCloseEvent) -> None:
        if self._export_running:
            event.ignore()
            return
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

    sync_callback = getattr(window, "_sync_current_project", None)
    if callable(sync_callback):
        try:
            project_path = sync_callback()
        except Exception as error:
            QMessageBox.critical(window, "Preview save error", str(error))
            return
    else:
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
    use_ai_preparation = bool(
        getattr(window, "ai_prepare_checkbox", None)
        and window.ai_prepare_checkbox.isChecked()
    )

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
        def export_callback(output_path: str) -> Path:
            return export_project_loop(
                project_path,
                shape_id,
                output_path,
                card_override=card_override,
                direction_override=direction_override,
                frame_count=72,
                fps=24,
                crf=18,
                seed=shape_id,
                use_ai_preparation=use_ai_preparation,
                prepared_assets_dir=result.assets_dir,
            )

        default_export_path = Path(project_path).with_name(
            "result_deterministic.mp4"
        )
        dialog = EffectPreviewDialog(
            result,
            window,
            export_callback=export_callback,
            default_export_path=default_export_path,
        )
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
        use_ai_preparation=use_ai_preparation,
    )
