import json
import math
import os
import tempfile
import time
import traceback
from typing import Optional, Tuple, Callable

from PySide6.QtCore import QStringListModel, QThread, QObject, Signal, Qt, QTimer
from PySide6.QtGui import QFont, QFontMetrics
from PySide6.QtGui import QPainter
from PySide6.QtWidgets import (
    QMainWindow, QGraphicsScene, QGraphicsView, QLabel, QFrame, QSizePolicy,
    QFormLayout, QFileDialog, QMessageBox, QProgressBar, QHBoxLayout,
    QGridLayout, QSpinBox, QDoubleSpinBox, QSlider, QButtonGroup
)
from PySide6.QtWidgets import QWidget, QVBoxLayout, QPushButton, QListView, QAbstractItemView

from tool_Params import TOOL_PARAMETERS
from ui_ai_window import Ui_MainWindow
from ui_fire_tool import Ui_fire_tool
from ui_light_tool import Ui_light_tool
from ui_water_tool import Ui_water_tool
from ui_weather_tool import Ui_weather_tool


# ---------------------------
# Render (SVD img2vid) логика
# ---------------------------
# Эта часть не трогает UI-файлы (ui_ai_window.py).
# Нажатие кнопки "render" запускает генерацию видео в отдельном потоке.


def _round_to_multiple(x: int, m: int = 64) -> int:
    return int(math.ceil(x / m) * m)


def _resolve_maybe_relative(path_str: str, base_dir: str) -> str:
    """Если path_str относительный — резолвим от base_dir."""
    if not path_str:
        return path_str
    if os.path.isabs(path_str) and os.path.exists(path_str):
        return path_str
    # пробуем как есть
    if os.path.exists(path_str):
        return path_str
    # пробуем относительно base_dir
    cand = os.path.join(base_dir, path_str)
    return cand


def _find_first_existing(*candidates: str) -> Optional[str]:
    for c in candidates:
        if c and os.path.exists(c):
            return c
    return None


def _svg_declared_size(svg_path: str) -> Optional[Tuple[float, float]]:
    """Пытаемся понять, SVG "на весь фон" или локальный. Возвращает (w,h) из viewBox/width/height, если получилось."""
    try:
        import xml.etree.ElementTree as ET
        tree = ET.parse(svg_path)
        root = tree.getroot()
        vb = root.attrib.get("viewBox") or root.attrib.get("viewbox")
        if vb:
            parts = vb.replace(",", " ").split()
            if len(parts) == 4:
                w = float(parts[2]);
                h = float(parts[3])
                if w > 0 and h > 0:
                    return (w, h)

        # width/height могут быть в px
        def _to_float(s: str) -> Optional[float]:
            if not s: return None
            s = s.strip().lower().replace("px", "")
            try:
                return float(s)
            except:
                return None

        w = _to_float(root.attrib.get("width", ""))
        h = _to_float(root.attrib.get("height", ""))
        if w and h and w > 0 and h > 0:
            return (w, h)
    except Exception:
        return None
    return None


def rasterize_svg_to_mask(svg_path: str, width: int, height: int, feather_px: int = 5):
    """SVG -> PIL маска (L) размера width x height. Требует PySide6-Addons (QtSvg)."""
    try:
        from PySide6.QtGui import QImage, QPainter
        from PySide6.QtSvg import QSvgRenderer
    except Exception as e:
        raise RuntimeError("QtSvg не доступен. Установи: python -m pip install PySide6-Addons") from e

    img = QImage(width, height, QImage.Format_ARGB32_Premultiplied)
    img.fill(Qt.transparent)
    renderer = QSvgRenderer(svg_path)
    p = QPainter(img)
    renderer.render(p)
    p.end()

    ptr = img.bits()
    ptr.setsize(img.sizeInBytes())
    import numpy as np
    arr = np.frombuffer(ptr, np.uint8).reshape((height, img.bytesPerLine() // 4, 4))
    arr = arr[:, :width, :]
    alpha = arr[..., 3]
    from PIL import Image, ImageFilter
    mask = Image.fromarray(alpha, mode="L")
    if feather_px and feather_px > 0:
        mask = mask.filter(ImageFilter.GaussianBlur(radius=feather_px))
    return mask


def _alpha_blend(dst_rgba_np, src_rgb_pil, alpha_mask_L_pil, top_left_xy):
    """Наложение src_rgb на dst_rgba по маске alpha_mask (L)."""
    import numpy as np
    x0, y0 = top_left_xy
    src = np.array(src_rgb_pil.convert("RGB"), dtype=np.uint8)
    a = np.array(alpha_mask_L_pil, dtype=np.uint8)  # HxW
    h, w = a.shape
    roi = dst_rgba_np[y0:y0 + h, x0:x0 + w, :].astype(np.float32)
    src_f = src.astype(np.float32)
    a_f = (a.astype(np.float32) / 255.0)[..., None]
    roi[..., :3] = src_f * a_f + roi[..., :3] * (1.0 - a_f)
    roi[..., 3] = 255
    dst_rgba_np[y0:y0 + h, x0:x0 + w, :] = roi.astype(np.uint8)
    return dst_rgba_np


def _load_svd_pipeline(device: str = "cuda"):
    """
    Ленивая загрузка SVD. Требует: torch, diffusers, transformers, accelerate, safetensors.
    Делает понятную ошибку с командой установки именно в текущий интерпретатор.
    """
    import sys, importlib.util

    def _need(pkg: str):
        return importlib.util.find_spec(pkg) is None

    missing = []
    for pkg in ("torch", "diffusers", "transformers", "accelerate", "safetensors"):
        if _need(pkg):
            missing.append(pkg)

    if missing:
        # покажем команду, которая точно ставит в тот Python, которым запущено приложение
        cmd = f'"{sys.executable}" -m pip install -U ' + " ".join(missing)
        raise RuntimeError(
            "Не найдены зависимости для SVD: " + ", ".join(missing) + "\n\n"
                                                                      "Установи их В ЭТОТ интерпретатор (тот, которым запущено приложение):\n"
                                                                      f"{cmd}\n\n"
                                                                      "Подсказка: если у тебя есть venv, убедись что приложение запускается из него."
        )

    # теперь можно импортировать
    import torch
    from diffusers import StableVideoDiffusionPipeline

    model_id = "stabilityai/stable-video-diffusion-img2vid-xt"
    dtype = torch.float16 if device.startswith("cuda") else torch.float32

    pipe = StableVideoDiffusionPipeline.from_pretrained(
        model_id,
        torch_dtype=dtype,
        variant="fp16" if dtype == torch.float16 else None
    )

    if device.startswith("cuda"):
        pipe.to(device)
        try:
            pipe.enable_xformers_memory_efficient_attention()
        except Exception:
            pass
    else:
        pipe.to("cpu")

    try:
        pipe.enable_model_cpu_offload()
    except Exception:
        pass

    return pipe


def _svd_generate_frames(pipe, pil_image_rgb, fps: int, num_frames: int, seed: int,
                         motion_bucket_id: int = 127, noise_aug_strength: float = 0.02, decode_chunk_size: int = 2):
    import torch
    from PIL import Image
    w, h = pil_image_rgb.size
    rw, rh = _round_to_multiple(w, 64), _round_to_multiple(h, 64)
    # чтобы не искажать, паддим до кратности 64
    if (rw, rh) != (w, h):
        padded = Image.new("RGB", (rw, rh))
        padded.paste(pil_image_rgb, (0, 0))
        inp = padded
    else:
        inp = pil_image_rgb

    g = torch.Generator(device=pipe.device if hasattr(pipe, "device") else "cpu")
    g.manual_seed(seed)
    out = pipe(
        inp, fps=fps, num_frames=num_frames, motion_bucket_id=motion_bucket_id,
        noise_aug_strength=noise_aug_strength, decode_chunk_size=decode_chunk_size, generator=g
    )
    frames = out.frames[0]
    # обратно к исходному размеру
    if (rw, rh) != (w, h):
        frames = [f.crop((0, 0, w, h)) for f in frames]
    return frames


def render_svd_from_project(shapes_json_path: str,
                            out_mp4_path: str,
                            masks_dir: Optional[str] = None,
                            pieces_dir: Optional[str] = None,
                            fps: int = 7,
                            num_frames: int = 25,
                            pad: int = 32,
                            feather_px: int = 5,
                            progress_cb: Optional[Callable[[int, int, int], None]] = None):
    """
    Рендер: для каждого shape берём кусок (shape_<id>.png), анимируем SVD и вклеиваем обратно по SVG-маске.
    Ожидаем структуру проекта рядом с shapes.json:
      - masks/shape_<id>.svg (или просто рядом)
      - shape_<id>.png (или в pieces/)
      - without_shape_area.png (желательно) как база для склейки
    """
    base_dir = os.path.dirname(shapes_json_path)
    with open(shapes_json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    bg_path = _resolve_maybe_relative(data.get("background", ""), base_dir)
    # если рядом есть "without_shape_area.png" — используем как базу, иначе берём фон
    base_bg_path = _find_first_existing(
        os.path.join(base_dir, "without_shape_area.png"),
        os.path.join(base_dir, "without_shape_area.jpg"),
        os.path.join(base_dir, "without_shape_area.jpeg"),
    )
    from PIL import Image
    background = Image.open(bg_path).convert("RGB")
    base_bg = Image.open(base_bg_path).convert("RGB") if base_bg_path else background.copy()
    W, H = background.size

    shapes = data.get("shapes", [])
    if not shapes:
        raise RuntimeError("В shapes.json нет списка shapes")

    if masks_dir is None:
        masks_dir = _find_first_existing(os.path.join(base_dir, "masks")) or base_dir
    if pieces_dir is None:
        pieces_dir = _find_first_existing(os.path.join(base_dir, "pieces")) or base_dir

    import numpy as np
    base_frames = []
    base_np = np.array(base_bg, dtype=np.uint8)
    rgba0 = np.dstack([base_np, np.full((H, W), 255, dtype=np.uint8)])
    for _ in range(num_frames):
        base_frames.append(rgba0.copy())

    # устройство
    try:
        import torch
        device = "cuda" if torch.cuda.is_available() else "cpu"
    except Exception:
        device = "cpu"

    pipe = _load_svd_pipeline(device=device)

    total = len(shapes)
    for i, sh in enumerate(shapes, start=1):
        sid = int(sh.get("id"))
        x = int(sh.get("x"));
        y = int(sh.get("y"))
        w = int(sh.get("width"));
        h = int(sh.get("height"))

        # padded bbox
        x0 = max(0, x - pad);
        y0 = max(0, y - pad)
        x1 = min(W, x + w + pad);
        y1 = min(H, y + h + pad)
        pw, ph = (x1 - x0), (y1 - y0)
        offx, offy = (x - x0), (y - y0)

        # входной патч = фон + кусок (если есть)
        patch_bg = background.crop((x0, y0, x1, y1)).convert("RGB")
        piece_path = _find_first_existing(
            os.path.join(pieces_dir, f"shape_{sid}.png"),
            os.path.join(base_dir, f"shape_{sid}.png"),
        )
        if piece_path:
            piece = Image.open(piece_path).convert("RGBA")
            if piece.size != (w, h):
                piece = piece.resize((w, h), Image.LANCZOS)
            # накладываем кусок на патч фона
            patch_rgba = patch_bg.convert("RGBA")
            patch_rgba.paste(piece, (offx, offy), piece)
            patch_input = patch_rgba.convert("RGB")
            piece_alpha = piece.split()[-1]
        else:
            patch_input = patch_bg
            piece_alpha = None

        # маска
        svg_path = _find_first_existing(
            os.path.join(masks_dir, f"shape_{sid}.svg"),
            os.path.join(base_dir, f"shape_{sid}.svg"),
        )
        if not svg_path and piece_alpha is None:
            raise RuntimeError(f"Не нашёл ни SVG маску, ни PNG с альфой для shape_{sid}")

        if svg_path:
            declared = _svg_declared_size(svg_path)
            full_svg = False
            if declared:
                # если SVG примерно размера фона — считаем full-size
                if abs(declared[0] - W) < W * 0.05 and abs(declared[1] - H) < H * 0.05:
                    full_svg = True
            if full_svg:
                mask_full = rasterize_svg_to_mask(svg_path, W, H, feather_px=feather_px)
                mask_patch = mask_full.crop((x0, y0, x1, y1))
            else:
                # локальная маска под bbox
                local = rasterize_svg_to_mask(svg_path, w, h, feather_px=feather_px)
                from PIL import Image as PILImage
                mask_patch = PILImage.new("L", (pw, ph), 0)
                mask_patch.paste(local, (offx, offy))
        else:
            # берём альфу из PNG
            from PIL import Image as PILImage
            mask_patch = PILImage.new("L", (pw, ph), 0)
            mask_patch.paste(piece_alpha, (offx, offy))

        # SVD
        frames_piece = _svd_generate_frames(
            pipe, patch_input, fps=fps, num_frames=num_frames, seed=123 + sid * 100
        )

        # вклейка
        for t in range(num_frames):
            base_frames[t] = _alpha_blend(base_frames[t], frames_piece[t], mask_patch, (x0, y0))

        if progress_cb:
            progress_cb(i, total, sid)

    # экспорт видео
    import imageio
    os.makedirs(os.path.dirname(out_mp4_path) or ".", exist_ok=True)
    writer = imageio.get_writer(
        out_mp4_path,
        fps=fps,
        format="FFMPEG",
        codec="libx264",
        pixelformat="yuv420p"
    )

    for t in range(num_frames):
        writer.append_data(base_frames[t][..., :3])
    writer.close()
    return out_mp4_path


class RenderWorker(QObject):
    progress = Signal(str)
    finished = Signal(str)
    error = Signal(str)

    def __init__(self, shapes_json_path: str, out_mp4_path: str, masks_dir: Optional[str], pieces_dir: Optional[str]):
        super().__init__()
        self.shapes_json_path = shapes_json_path
        self.out_mp4_path = out_mp4_path
        self.masks_dir = masks_dir
        self.pieces_dir = pieces_dir

    def run(self):
        try:
            def cb(i, total, sid):
                self.progress.emit(f"{i}/{total} (shape {sid})")

            out = render_svd_from_project(
                self.shapes_json_path, self.out_mp4_path,
                masks_dir=self.masks_dir, pieces_dir=self.pieces_dir,
                progress_cb=cb
            )
            self.finished.emit(out)
        except Exception as e:
            tb = traceback.format_exc()
            self.error.emit(str(e) + "\n\n" + tb)


class InSceneComboBox(QWidget):
    def __init__(self, options=None, parent=None):
        super().__init__(parent)
        self.options = options or ["default", "low", "normal", "high"]
        self.selected = self.options[0]

        self.button = QPushButton(self.selected)
        self.button.setStyleSheet("""
            QPushButton {
                background-color: #2a2a2a;
                color: white;
                border: 1px solid #555;
                padding: 2px 6px;
                text-align: left;
            }
            QPushButton::menu-indicator {
                image: none;
            }
        """)

        self.view = QListView()
        self.view.setStyleSheet("""
            QListView {
                background-color: #2a2a2a;
                color: white;
                border: 1px solid #555;
                selection-background-color: #444;
                padding: 2px;
            }
        """)
        self.view.setWindowFlags(Qt.Popup)
        self.view.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.view.setSelectionMode(QAbstractItemView.SingleSelection)

        self.model = QStringListModel(self.options)
        self.view.setModel(self.model)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.button)

        self.button.clicked.connect(self.show_popup)
        self.view.clicked.connect(self.select_option)

    def show_popup(self):
        popup_width = max(self.width(), 100)
        self.view.setFixedWidth(popup_width)

        # Убираем скролл
        self.view.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        # Подсветка каждой строки (граница снизу)
        self.view.setStyleSheet("""
            QListView {
                background-color: #2a2a2a;
                color: white;
                border: 1px solid #555;
                selection-background-color: #444;
                padding: 2px;
            }
            QListView::item {
                border-bottom: 1px solid #444;
                padding: 4px;
            }
        """)

        row_height = self.view.sizeHintForRow(0) or 20
        max_visible = min(len(self.options), 5)
        total_height = max_visible * row_height + 4
        self.view.setFixedHeight(total_height)

        self.view.move(self.mapToGlobal(self.button.rect().bottomLeft()))
        self.view.show()

    def select_option(self, index):
        value = self.model.data(index)
        self.selected = value
        self.button.setText(value)
        self.view.hide()

    def setCurrentText(self, text):
        if text in self.options:
            self.selected = text
            self.button.setText(text)

    def addItems(self, items):
        self.options = items
        self.model.setStringList(items)
        self.setCurrentText(items[0] if items else "select")




class MotionSettingsWidget(QFrame):
    """Compact, loop-safe motion controls for one selected image area."""

    changed = Signal()

    _QUICK_DIRECTIONS = (
        ("↖", 225), ("↑", 270), ("↗", 315),
        ("←", 180), ("→", 0),
        ("↙", 135), ("↓", 90), ("↘", 45),
    )

    def __init__(self, parent=None):
        super().__init__(parent)
        self._configured = False
        self._loading = False
        self._exact_direction = None
        self.setObjectName("motionSettings")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        title_row = QHBoxLayout()
        title = QLabel("Motion")
        title.setObjectName("sectionTitle")
        self.direction_label = QLabel("→  Right")
        self.direction_label.setObjectName("motionSummary")
        title_row.addWidget(title)
        title_row.addStretch(1)
        title_row.addWidget(self.direction_label)
        layout.addLayout(title_row)

        direction_grid = QGridLayout()
        direction_grid.setSpacing(3)
        positions = ((0, 0), (0, 1), (0, 2), (1, 0), (1, 2), (2, 0), (2, 1), (2, 2))
        for (text, angle), (row, column) in zip(self._QUICK_DIRECTIONS, positions):
            button = QPushButton(text)
            button.setObjectName("directionButton")
            button.setFixedSize(32, 26)
            button.setToolTip(f"Set direction to {angle}°")
            button.clicked.connect(lambda _checked=False, value=angle: self.set_angle(value))
            direction_grid.addWidget(button, row, column)

        angle_row = QHBoxLayout()
        angle_row.addLayout(direction_grid)
        angle_row.addSpacing(6)
        angle_label = QLabel("Angle")
        self.angle_spin = QSpinBox()
        self.angle_spin.setObjectName("motionAngle")
        self.angle_spin.setRange(0, 359)
        self.angle_spin.setSuffix("°")
        self.angle_spin.setWrapping(True)
        self.angle_spin.setToolTip("0° right, 90° down, 180° left, 270° up")
        angle_row.addWidget(angle_label)
        angle_row.addWidget(self.angle_spin)
        angle_row.addStretch(1)
        layout.addLayout(angle_row)

        self.strength_slider, self.strength_spin = self._add_value_row(
            layout, "Amplitude", "motionStrength", 1, 20, 4, " px"
        )
        self.cycles_slider, self.cycles_spin = self._add_value_row(
            layout, "Speed", "motionCycles", 1, 4, 1, " cycles"
        )
        self.cycles_spin.setToolTip(
            "Whole cycles per loop; integer values keep the animation seamless"
        )

        self.angle_spin.valueChanged.connect(self._on_angle_changed)
        self.strength_spin.valueChanged.connect(self._on_value_changed)
        self.cycles_spin.valueChanged.connect(self._on_value_changed)
        self._update_direction_label()

    @staticmethod
    def _add_value_row(layout, label_text, object_name, minimum, maximum, value, suffix):
        row = QHBoxLayout()
        label = QLabel(label_text)
        label.setMinimumWidth(68)
        slider = QSlider(Qt.Orientation.Horizontal)
        slider.setObjectName(f"{object_name}Slider")
        slider.setRange(minimum, maximum)
        slider.setValue(value)
        spin = QSpinBox()
        spin.setObjectName(object_name)
        spin.setRange(minimum, maximum)
        spin.setValue(value)
        spin.setSuffix(suffix)
        spin.setFixedWidth(82)
        slider.valueChanged.connect(spin.setValue)
        spin.valueChanged.connect(slider.setValue)
        row.addWidget(label)
        row.addWidget(slider, 1)
        row.addWidget(spin)
        layout.addLayout(row)
        return slider, spin

    def apply_profile(self, profile):
        """Apply effect-safe motion ranges without discarding saved direction."""
        max_strength = max(1, round(float(profile.get("max_strength", 20))))
        max_cycles = max(1, round(float(profile.get("max_cycles", 4))))
        recommended_strength = max(
            1,
            min(
                max_strength,
                round(float(profile.get("recommended_strength", 4))),
            ),
        )
        recommended_cycles = max(
            1,
            min(
                max_cycles,
                round(float(profile.get("recommended_cycles", 1))),
            ),
        )
        was_configured = self._configured
        previous = (self.strength_spin.value(), self.cycles_spin.value())
        self._loading = True
        try:
            for control in (self.strength_slider, self.strength_spin):
                control.setMaximum(max_strength)
            for control in (self.cycles_slider, self.cycles_spin):
                control.setMaximum(max_cycles)
            if was_configured:
                self.strength_spin.setValue(min(previous[0], max_strength))
                self.cycles_spin.setValue(min(previous[1], max_cycles))
            else:
                self.strength_spin.setValue(recommended_strength)
                self.cycles_spin.setValue(recommended_cycles)
        finally:
            self._loading = False
        self._configured = was_configured
        self.strength_spin.setToolTip(
            f"Recommended {recommended_strength} px; safe maximum {max_strength} px"
        )
        self.cycles_spin.setToolTip(
            f"Recommended {recommended_cycles}; safe maximum {max_cycles} loop cycles"
        )
        current = (self.strength_spin.value(), self.cycles_spin.value())
        if was_configured and current != previous:
            self.changed.emit()

    @property
    def configured(self):
        return self._configured

    def _on_value_changed(self, _value=None):
        self._update_direction_label()
        if self._loading:
            return
        self._configured = True
        self.changed.emit()

    def _on_angle_changed(self, value=None):
        if not self._loading:
            self._exact_direction = None
        self._on_value_changed(value)

    def _update_direction_label(self):
        angle = self.angle_spin.value()
        names = {
            0: "→  Right", 45: "↘  Down-right", 90: "↓  Down",
            135: "↙  Down-left", 180: "←  Left", 225: "↖  Up-left",
            270: "↑  Up", 315: "↗  Up-right",
        }
        self.direction_label.setText(names.get(angle, f"{angle}°"))

    def set_angle(self, angle_deg, *, configured=True):
        self._exact_direction = None
        previous_loading = self._loading
        self._loading = not configured
        previous_angle = self.angle_spin.value()
        self.angle_spin.setValue(round(float(angle_deg)) % 360)
        self._loading = previous_loading
        if configured:
            self._configured = True
            if self.angle_spin.value() == previous_angle:
                self.changed.emit()
        self._update_direction_label()

    def set_motion(self, motion, *, configured=True):
        if not isinstance(motion, dict):
            return
        from effect_engine.project import angle_from_direction
        from effect_engine.project import normalize_direction

        angle = motion.get("angle_deg")
        try:
            angle = float(angle)
        except (TypeError, ValueError):
            angle = angle_from_direction(motion.get("direction"), self.angle_spin.value())
        try:
            strength = round(float(motion.get("strength", 4)))
        except (TypeError, ValueError):
            strength = 4
        try:
            cycles = round(float(motion.get("cycles", 1)))
        except (TypeError, ValueError):
            cycles = 1
        exact_direction = normalize_direction(motion.get("direction"))
        self._loading = True
        try:
            self.angle_spin.setValue(round(angle) % 360)
            self.strength_spin.setValue(strength)
            self.cycles_spin.setValue(cycles)
        finally:
            self._loading = False
        self._configured = bool(configured)
        self._exact_direction = exact_direction
        self._update_direction_label()

    def motion_data(self):
        from effect_engine.project import direction_from_angle

        angle = self.angle_spin.value()
        direction = self._exact_direction or direction_from_angle(angle)
        return {
            "angle_deg": angle,
            "direction": [round(direction[0], 8), round(direction[1], 8)],
            "strength": self.strength_spin.value(),
            "cycles": self.cycles_spin.value(),
        }


class ShapeCard(QWidget):
    motion_changed = Signal(int, object)

    def __init__(self, shape_id, shape_type, color_name):
        super().__init__()
        self.shape_id = shape_id
        self.setFocusPolicy(Qt.NoFocus)


        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(4, 4, 4, 4)
        self.main_layout.setSpacing(4)

        header = QWidget()
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(4)
        label = QLabel(f"{shape_type}  ·  Area {shape_id}")
        label.setObjectName("shapeCardTitle")
        label.setStyleSheet(f"""
            color: white;
            border: 2px solid {color_name};
            padding: 2px;
        """)
        label.setFocusPolicy(Qt.NoFocus)
        reset_button = QPushButton("Reset effects")
        reset_button.setObjectName("resetEffectsButton")
        reset_button.setToolTip("Remove the selected preset and legacy secondary settings")
        reset_button.clicked.connect(self.clear_effects)
        header_layout.addWidget(label, 1)
        header_layout.addWidget(reset_button)
        self.main_layout.addWidget(header)

        self.frame = QFrame()
        self.frame.setStyleSheet(f"""
            background-color: transparent;
            border: 2px solid {color_name};
            border-radius: 4px;
        """)
        self.main_layout.addWidget(self.frame)

        self.frame_layout = QVBoxLayout(self.frame)
        self.frame_layout.setContentsMargins(4, 4, 4, 4)
        self.frame_layout.setSpacing(4)

        self.motion_controls = MotionSettingsWidget(self.frame)
        self.motion_controls.changed.connect(self._emit_motion_changed)
        self.frame_layout.addWidget(self.motion_controls)

        self.tool_type = None
        self.main_function_added = False
        self.added_subfunctions = set()

    def _emit_motion_changed(self):
        self.motion_changed.emit(int(self.shape_id), self.motion_controls.motion_data())

    def set_motion(self, motion, *, configured=True):
        self.motion_controls.set_motion(motion, configured=configured)

    def motion_data(self):
        return self.motion_controls.motion_data()

    def clear_effects(self):
        """Remove effect blocks while keeping motion controls and area identity."""
        for index in range(self.frame_layout.count() - 1, -1, -1):
            item = self.frame_layout.itemAt(index)
            widget = item.widget() if item else None
            if widget is None or widget is self.motion_controls:
                continue
            self.frame_layout.takeAt(index)
            widget.deleteLater()
        self.tool_type = None
        self.main_function_added = False
        self.added_subfunctions.clear()


from PySide6.QtWidgets import QGraphicsWidget, QGraphicsLinearLayout, QGraphicsProxyWidget
from PySide6.QtWidgets import QGraphicsItem

class ShapeCardGraphicsWidget(QGraphicsWidget):
    def __init__(self, shape_id, shape_widget, parent_window):
        super().__init__()
        self.shape_id = shape_id
        self.parent_window = parent_window

        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
        self.setAcceptedMouseButtons(Qt.LeftButton)

        layout = QGraphicsLinearLayout(Qt.Vertical)
        proxy = QGraphicsProxyWidget(self)
        proxy.setWidget(shape_widget)
        layout.addItem(proxy)

        self.setLayout(layout)

    def mousePressEvent(self, event):
        self.setSelected(True)
        if self.parent_window:
            self.parent_window.select_shape_card(self.shape_id)
        super().mousePressEvent(event)


class AIWindow(QMainWindow):
    motion_changed = Signal(int, object)

    def __init__(self):
        super().__init__()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self.setWindowTitle("AI Effects")
        self.project_sync_callback = None
        self.selected_shape_id = None
        if hasattr(self.ui, "pushButton"):
            self.ui.pushButton.setText("AI render")
            self.ui.pushButton.setToolTip(
                "Stable Video Diffusion render; requires backend_server.py"
            )
        if hasattr(self.ui, "pushButton_9"):
            self.ui.pushButton_9.setText("Save effects")
            self.ui.pushButton_9.setToolTip(
                "Update effect settings in the current shapes.json project"
            )
            self.ui.pushButton_9.clicked.connect(self.save_effects_to_project)

        self.render_status_label = QLabel("AI: ready", self)
        self.render_status_label.setMinimumWidth(260)
        self.render_status_label.setToolTip("Текущий этап AI-рендера")
        self.render_progress_bar = QProgressBar(self)
        self.render_progress_bar.setFixedWidth(180)
        self.render_progress_bar.setTextVisible(True)
        self.render_progress_bar.hide()
        top_layout = getattr(self.ui, "horizontalLayout_3", None)
        if top_layout is not None:
            insert_at = max(0, top_layout.count() - 1)
            top_layout.insertWidget(insert_at, self.render_status_label)
            top_layout.insertWidget(insert_at + 1, self.render_progress_bar)

        self.scene = QGraphicsScene(self)
        self.ui.graphicsView.setRenderHint(QPainter.Antialiasing)
        self.ui.graphicsView.setScene(self.scene)
        self.ui.graphicsView.setDragMode(QGraphicsView.NoDrag)
        self.ui.graphicsView.setStyleSheet("background-color: #1e1e1e; border: none;")
        self.ui.graphicsView.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.ui.graphicsView.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        self.ui.water_button.setText("Water")
        self.ui.fire_button.setText("Fire")
        self.ui.light_button.setText("Light")
        self.ui.weather_tool.setText("Weather")
        self.ui.water_button.setToolTip(
            "Water presets are supported by Local Preview and AI render"
        )
        self.ui.weather_tool.setToolTip(
            "Rain presets are supported by the deterministic Local Preview"
        )
        for button in (
            self.ui.fire_button,
            self.ui.light_button,
        ):
            button.setEnabled(False)
            button.setToolTip("Renderer not implemented yet")
        self.ui.label_13.setText("Selected area:")
        self.tool_button_group = QButtonGroup(self)
        self.tool_button_group.setExclusive(True)
        for button in (
            self.ui.water_button,
            self.ui.fire_button,
            self.ui.light_button,
            self.ui.weather_tool,
        ):
            button.setCheckable(True)
            self.tool_button_group.addButton(button)

        self.ui.weather_tool.clicked.connect(lambda: self.load_tool_panel(Ui_weather_tool))
        self.ui.water_button.clicked.connect(lambda: self.load_tool_panel(Ui_water_tool))
        self.ui.light_button.clicked.connect(lambda: self.load_tool_panel(Ui_light_tool))
        self.ui.fire_button.clicked.connect(lambda: self.load_tool_panel(Ui_fire_tool))

        # --- Render (SVD img2vid) ---
        # Кнопка render в ui_ai_window.py: self.pushButton (text "render")
        if hasattr(self.ui, "pushButton"):
            self.ui.pushButton.clicked.connect(self.on_render_clicked)
        self.render_shapes_json_path = None
        self.render_masks_dir = None
        self.render_pieces_dir = None
        self.render_out_mp4_path = None
        self._render_thread = None
        self._render_worker = None

        self._svd_job_id = None
        self._svd_poll_in_flight = False
        self._svd_status_failures = 0
        self._svd_started_at = None
        self._last_svd_progress_key = None
        self._svd_timer = QTimer(self)
        self._svd_timer.timeout.connect(self._poll_svd_status)


        self.shape_cards = {}
        self.last_tool_type = None

        self.tool_container_layout = QVBoxLayout(self.ui.scrollAreaWidgetContents)
        self.tool_container_layout.setSpacing(6)
        self.tool_container_layout.setContentsMargins(8, 8, 8, 8)
        self.tool_panel_title = QLabel("Effect presets")
        self.tool_panel_title.setObjectName("panelTitle")
        self.tool_container_layout.addWidget(self.tool_panel_title)
        self._active_tool_widget = None
        self._apply_ai_panel_style()

    def _apply_ai_panel_style(self):
        self.setStyleSheet("""
            QMainWindow, QWidget#centralwidget { background: #0f172a; color: #e5e7eb; }
            QFrame#frame_2 { background: #111827; border-bottom: 1px solid #263247; }
            QPushButton {
                min-height: 28px; padding: 4px 10px; color: #dbeafe;
                background: #1e293b; border: 1px solid #334155; border-radius: 6px;
            }
            QPushButton:hover { background: #29384f; border-color: #64748b; }
            QPushButton:checked { background: #164e63; border-color: #22d3ee; color: white; }
            QPushButton#pushButton { background: #2563eb; border-color: #3b82f6; color: white; font-weight: 600; }
            QPushButton#pushButton:hover { background: #1d4ed8; }
            QPushButton#pushButton_9 { background: #17344f; border-color: #25678c; }
            QLabel#panelTitle { color: #f8fafc; font-size: 15px; font-weight: 700; padding: 4px 2px; }
            QLabel#shapeCardTitle { color: #f8fafc; font-weight: 700; border-radius: 6px; padding: 6px; }
            QLabel#sectionTitle { color: #f8fafc; font-weight: 700; }
            QLabel#motionSummary { color: #67e8f9; font-weight: 600; }
            QFrame#motionSettings { background: #111c2f; border: 1px solid #334155; border-radius: 7px; }
            QPushButton#directionButton { min-height: 0; padding: 0; font-size: 15px; }
            QPushButton#resetEffectsButton { min-height: 24px; padding: 2px 7px; color: #fca5a5; }
            QSpinBox, QDoubleSpinBox { background: #172033; color: #f8fafc; border: 1px solid #475569; border-radius: 5px; padding: 3px; }
            QProgressBar { color: #e5e7eb; background: #1e293b; border: 1px solid #334155; border-radius: 5px; text-align: center; }
            QProgressBar::chunk { background: #22c55e; border-radius: 4px; }
            QScrollArea { background: #0b1220; border: 1px solid #263247; border-radius: 7px; }
            QScrollArea > QWidget > QWidget { background: #0b1220; }
        """)

    def add_shape_card(self, shape_id, shape_type, color_name):
        shape_widget = ShapeCard(shape_id, shape_type, color_name)
        shape_widget.motion_changed.connect(self._on_card_motion_changed)
        widget = ShapeCardGraphicsWidget(shape_id, shape_widget, self)
        widget.setPos(40 + len(self.shape_cards) * 30, 40 + len(self.shape_cards) * 30)
        self.scene.addItem(widget)
        self.shape_cards[shape_id] = widget

        print(f"[DEBUG] ShapeCard created: ID = {shape_id}")

    def _on_card_motion_changed(self, shape_id, motion):
        self.motion_changed.emit(int(shape_id), dict(motion))
        self._set_render_status(
            f"Area {shape_id}: motion {motion['angle_deg']}°, "
            f"{motion['strength']} px, {motion['cycles']} cycle(s)",
            3500,
        )

    def set_shape_direction(self, shape_id, direction, *, notify=False):
        """Synchronize a direction selected in the main editor with its AI card."""
        from effect_engine.project import angle_from_direction, normalize_direction

        normalized = normalize_direction(direction)
        graphics_widget = self.shape_cards.get(int(shape_id))
        if normalized is None or graphics_widget is None:
            return False
        proxy = graphics_widget.layout().itemAt(0)
        shape_card = proxy.widget() if proxy else None
        if shape_card is None:
            return False
        motion = shape_card.motion_data()
        motion["direction"] = list(normalized)
        motion["angle_deg"] = round(angle_from_direction(normalized)) % 360
        shape_card.set_motion(motion, configured=True)
        if notify:
            self.motion_changed.emit(int(shape_id), shape_card.motion_data())
        return True

    def select_shape_card(self, shape_id) -> None:
        self.selected_shape_id = int(shape_id)
        if hasattr(self.ui, "label_14"):
            self.ui.label_14.setText(str(self.selected_shape_id))

    def _set_render_status(self, text: str, timeout: int = 0) -> None:
        message = str(text)
        self.statusBar().showMessage(message, int(timeout))
        if hasattr(self, "render_status_label"):
            self.render_status_label.setText(message)
            self.render_status_label.setToolTip(message)

    def clear_shape_cards(self):
        """Reset cards when a new image or project replaces the current scene."""
        self.scene.clear()
        self.shape_cards.clear()
        self.last_tool_type = None
        self.selected_shape_id = None
        if hasattr(self.ui, "label_14"):
            self.ui.label_14.clear()

    def reset_project_state(self):
        active_job_id = self._svd_job_id
        if active_job_id:
            from backend_async import run_in_thread
            import backend_client

            run_in_thread(
                self,
                backend_client.cancel_svd_render,
                lambda _result: None,
                lambda _message: None,
                active_job_id,
                timeout=5.0,
            )
        self.clear_shape_cards()
        self.render_shapes_json_path = None
        self.render_masks_dir = None
        self.render_pieces_dir = None
        self.render_out_mp4_path = None
        self._svd_job_id = None
        self._svd_poll_in_flight = False
        self._svd_status_failures = 0
        self._svd_started_at = None
        self._last_svd_progress_key = None
        if hasattr(self, "render_progress_bar"):
            self.render_progress_bar.hide()
        if hasattr(self.ui, "pushButton"):
            self.ui.pushButton.setEnabled(True)
            self.ui.pushButton.setText("AI render")
        self._svd_timer.stop()

    def remove_shape_card(self, shape_id):
        widget = self.shape_cards.pop(shape_id, None)
        if widget is not None and widget.scene() is self.scene:
            self.scene.removeItem(widget)
        if self.selected_shape_id == int(shape_id):
            self.selected_shape_id = None
            if hasattr(self.ui, "label_14"):
                self.ui.label_14.clear()

    @staticmethod
    def _normalize_effect_name(value):
        return "".join(ch for ch in str(value).casefold() if ch.isalnum())

    def _infer_effect_key(self, tool_type, display_name):
        """Resolve old project entries that were saved without a stable effect key."""
        target = self._normalize_effect_name(display_name)
        for param_key in TOOL_PARAMETERS:
            namespace, separator, button_name = param_key.partition(":")
            if not separator:
                button_name = namespace
            elif namespace != tool_type:
                continue

            visible_name = button_name.split("_", 1)[-1].replace("_", " ")
            if self._normalize_effect_name(visible_name) == target:
                return button_name
        try:
            from effect_engine.preset_registry import default_preset_registry

            for preset in default_preset_registry().list(tool_type):
                if self._normalize_effect_name(preset.label) == target:
                    return preset.editor_key or f"main_{preset.preset_id}"
        except (KeyError, ValueError):
            pass
        return None

    def restore_shape_cards_data(self, cards):
        """Restore saved effect blocks after the editor scene has been loaded."""
        if not isinstance(cards, list):
            return

        previous_tool = self.last_tool_type
        previous_selected_id = self.selected_shape_id

        for card_data in cards:
            if not isinstance(card_data, dict):
                continue
            try:
                shape_id = int(card_data.get("id"))
            except (TypeError, ValueError):
                continue
            graphics_widget = self.shape_cards.get(shape_id)
            tool_type = str(card_data.get("tool_type") or "").lower()
            if graphics_widget is None or not tool_type:
                continue

            panel_position = card_data.get("panel_position")
            if isinstance(panel_position, dict):
                try:
                    graphics_widget.setPos(
                        float(panel_position.get("x", graphics_widget.pos().x())),
                        float(panel_position.get("y", graphics_widget.pos().y())),
                    )
                except (TypeError, ValueError):
                    pass

            proxy = graphics_widget.layout().itemAt(0)
            shape_card = proxy.widget() if proxy else None
            if shape_card is None:
                continue

            motion = card_data.get("motion")
            if isinstance(motion, dict):
                shape_card.set_motion(motion, configured=True)

            entries = []
            if isinstance(card_data.get("main"), dict):
                entries.append(card_data["main"])
            elif card_data.get("preset_id"):
                try:
                    from effect_engine.preset_registry import resolve_card_preset

                    preset = resolve_card_preset(card_data, tool_type)
                except (KeyError, ValueError):
                    preset = None
                if preset is not None and preset.editor_key:
                    entries.append(
                        {
                            "key": preset.editor_key,
                            "name": preset.label,
                            "params": {},
                        }
                    )
            entries.extend(entry for entry in card_data.get("sub", []) if isinstance(entry, dict))

            self.last_tool_type = f"Ui_{tool_type}_tool"
            self.select_shape_card(shape_id)
            for entry in entries:
                display_name = str(entry.get("name") or "").strip()
                effect_key = str(entry.get("key") or "").strip()
                if not effect_key:
                    effect_key = self._infer_effect_key(tool_type, display_name) or ""
                if not effect_key:
                    continue
                if not display_name:
                    display_name = effect_key.split("_", 1)[-1].replace("_", " ")

                count_before = shape_card.frame_layout.count()
                self.add_button_name_to_shape_card(
                    display_name,
                    effect_key,
                    effect_type=tool_type,
                )
                if shape_card.frame_layout.count() == count_before:
                    continue

                block = shape_card.frame_layout.itemAt(shape_card.frame_layout.count() - 1).widget()
                form_layout = block.layout().itemAt(1) if block and block.layout() else None
                saved_params = entry.get("params") or {}
                if not isinstance(form_layout, QFormLayout) or not isinstance(saved_params, dict):
                    continue
                for row in range(form_layout.rowCount()):
                    label = form_layout.itemAt(row, QFormLayout.LabelRole).widget()
                    field = form_layout.itemAt(row, QFormLayout.FieldRole).widget()
                    if not label or not field:
                        continue
                    parameter_id = str(
                        field.property("parameter_id") or label.text()
                    )
                    if parameter_id in saved_params:
                        saved_value = saved_params[parameter_id]
                    elif label.text() in saved_params:
                        saved_value = saved_params[label.text()]
                    else:
                        continue
                    if hasattr(field, "selected"):
                        field.setCurrentText(str(saved_value))
                    elif isinstance(field, QSpinBox):
                        try:
                            field.setValue(round(float(saved_value)))
                        except (TypeError, ValueError):
                            pass
                    elif isinstance(field, QDoubleSpinBox):
                        try:
                            field.setValue(float(saved_value))
                        except (TypeError, ValueError):
                            pass

        self.last_tool_type = previous_tool
        if previous_selected_id is None:
            self.selected_shape_id = None
            if hasattr(self.ui, "label_14"):
                self.ui.label_14.clear()
        else:
            self.select_shape_card(previous_selected_id)

    def load_tool_panel(self, ui_class):
        self.last_tool_type = ui_class.__name__
        print(f"[DEBUG] Активирован инструмент: {self.last_tool_type}")

        if self._active_tool_widget is not None:
            self.tool_container_layout.removeWidget(self._active_tool_widget)
            self._active_tool_widget.deleteLater()
            self._active_tool_widget = None

        tool_widget = QWidget()
        ui = ui_class()
        ui.setupUi(tool_widget)
        panel_id = (
            ui_class.__name__.lower().removeprefix("ui_").removesuffix("_tool")
        )
        if panel_id == "weather":
            # The weather form still contains legacy fog/wind sub-controls.
            # Rain is the only registered deterministic weather plugin for now.
            ui.label_162.hide()
            ui.splitter_325.hide()
            ui.splitter_328.hide()

        from effect_engine.plugins import default_effect_plugin_registry

        panel_plugins = default_effect_plugin_registry().for_panel(panel_id)
        preset_by_key = {}
        if panel_plugins:
            from effect_engine.preset_registry import default_preset_registry

            registry = default_preset_registry()
            existing_keys = {
                button.objectName().casefold()
                for button in tool_widget.findChildren(QPushButton)
            }
            target_names = {plugin.panel_container for plugin in panel_plugins}
            if len(target_names) != 1:
                raise ValueError(
                    f"Effect plugins in panel '{panel_id}' use different containers"
                )
            target = getattr(ui, target_names.pop())
            for plugin in panel_plugins:
                effect_type = plugin.effect_type
                for preset in registry.list(effect_type):
                    editor_key = preset.editor_key or f"main_{preset.preset_id}"
                    preset_by_key[editor_key.casefold()] = preset
                    if editor_key.casefold() in existing_keys:
                        continue
                    button = QPushButton(preset.label, target)
                    button.setObjectName(editor_key)
                    target.addWidget(button)
                    existing_keys.add(editor_key.casefold())

        buttons = tool_widget.findChildren(QPushButton)
        print(f"[DEBUG] Найдено {len(buttons)} кнопок в {ui_class.__name__}")

        for btn in buttons:
            btn_text = btn.text().strip()
            btn_name = btn.objectName().strip()
            preset = preset_by_key.get(btn_name.casefold())
            supported = preset is not None
            if btn_name.casefold().startswith("sub_"):
                btn.setEnabled(False)
                btn.setToolTip("This secondary effect is saved only for compatibility")
                continue
            if (
                supported
                and btn_text
                and btn_text.casefold() not in {"x", "color"}
                and btn_name.casefold() not in {"x", "color"}
            ):
                btn.clicked.connect(
                    lambda _, text=btn_text, name=btn_name, effect=preset.effect_type:
                    self.add_button_name_to_shape_card(
                        text,
                        name,
                        effect_type=effect,
                    )
                )
                print(f"[DEBUG] Привязан обработчик к кнопке: {btn_text} ({btn_name})")
            elif btn_name.casefold().startswith("main_"):
                btn.setVisible(False)

        tool_widget._tool_class = ui_class
        size_policy = QSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        tool_widget.setSizePolicy(size_policy)
        self.tool_container_layout.addWidget(tool_widget)
        self._active_tool_widget = tool_widget

    def add_button_name_to_shape_card(
        self,
        button_text,
        button_name,
        *,
        effect_type=None,
    ):
        print(f"[DEBUG] Нажата кнопка: {button_text} ({button_name})")
        selected_id = self.selected_shape_id
        if selected_id is None:
            print("[DEBUG] ShapeCard не выбран")
            return
        print(f"[DEBUG] Выбран ShapeCard ID: {selected_id}")

        if selected_id not in self.shape_cards:
            print(f"[DEBUG] ShapeCard с ID {selected_id} не найден")
            return

        proxy = self.shape_cards[selected_id].layout().itemAt(0)
        shape_card = proxy.widget() if proxy else None

        if not shape_card:
            print(f"[DEBUG] [ERROR] Не удалось получить ShapeCard для ID {selected_id}")
            return

        tool_type = str(
            effect_type
            or self.last_tool_type.lower().replace('ui_', '').replace('_tool', '')
        ).lower()
        is_main = button_name.lower().startswith('main_')
        is_sub = button_name.lower().startswith('sub_')

        if shape_card.tool_type and shape_card.tool_type != tool_type:
            print(f"[DEBUG] [ERROR] Нельзя смешивать инструменты: {shape_card.tool_type} != {tool_type}")
            return

        if not shape_card.tool_type:
            shape_card.tool_type = tool_type
            print(f"[DEBUG] [OK] Назначен tool_type: {tool_type}")

        if is_main:
            if shape_card.main_function_added:
                print(f"[DEBUG] [WARN] Главная функция уже добавлена в ShapeCard {selected_id}")
                return
            shape_card.main_function_added = True
            print(f"[DEBUG] [OK] Добавлена главная функция: {button_text}")
            try:
                from effect_engine.parameters import motion_profile_from_card

                profile = motion_profile_from_card(
                    {
                        "tool_type": tool_type,
                        "main": {"key": button_name, "name": button_text},
                    }
                )
                shape_card.motion_controls.apply_profile(profile)
            except (KeyError, ValueError):
                pass
        elif is_sub:
            if button_name in shape_card.added_subfunctions:
                print(f"[DEBUG] [WARN] Саб-функция уже добавлена: {button_text} ({button_name})")
                return
            shape_card.added_subfunctions.add(button_name)
            print(f"[DEBUG] [ADD] Добавлена саб-функция: {button_text}")
        else:
            print(f"[DEBUG] [WARN] Неизвестный тип кнопки: {button_text} ({button_name})")
            return

        # Добавление параметров
        param_block = QVBoxLayout()
        label = QLabel(button_text)
        if is_sub:
            label.setToolTip(
                "Legacy secondary setting: preserved in the project but not rendered"
            )
        label.setStyleSheet("color: white; font-weight: bold;")
        param_block.addWidget(label)

        parameter_definitions = ()
        params = []
        if is_main:
            try:
                from effect_engine.parameter_schema import (
                    default_parameter_schema_registry,
                )
                from effect_engine.preset_registry import default_preset_registry

                preset = default_preset_registry().resolve(tool_type, button_name)
                parameter_definitions = default_parameter_schema_registry().get(
                    tool_type
                ).select(preset.controls)
            except KeyError:
                parameter_definitions = ()
        if not parameter_definitions:
            params = TOOL_PARAMETERS.get(
                f"{tool_type}:{button_name}",
                TOOL_PARAMETERS.get(button_name, []),
            )
        from PySide6.QtWidgets import QFormLayout  # обязательно добавить в импорты

        form_layout = QFormLayout()
        form_layout.setSpacing(6)
        form_layout.setContentsMargins(0, 0, 0, 0)

        font = QFont()
        font.setPointSize(12)
        metrics = QFontMetrics(font)
        display_parameters = (
            [definition.label for definition in parameter_definitions]
            if parameter_definitions
            else list(params)
        )
        max_width = max(
            (metrics.horizontalAdvance(p) for p in display_parameters),
            default=0,
        ) + 10

        for index, param in enumerate(display_parameters):
            definition = parameter_definitions[index] if parameter_definitions else None
            label = QLabel(param)
            label.setWordWrap(False)
            label.setStyleSheet(f"""
                color: lightgray;
                font-size: 12px;
                min-width: {max_width}px;
                max-width: {max_width}px;
            """)

            if definition is None or definition.kind == "enum":
                field = InSceneComboBox()
                options = list(definition.options) if definition else [
                    "none", "default", "weak", "normal", "strong"
                ]
                field.addItems(options)
                field.setCurrentText(
                    str(definition.default) if definition else "default"
                )
            elif definition.kind == "int":
                field = QSpinBox()
                field.setRange(
                    round(
                        definition.minimum
                        if definition.minimum is not None
                        else 0
                    ),
                    round(
                        definition.maximum
                        if definition.maximum is not None
                        else 100
                    ),
                )
                field.setSingleStep(max(1, round(definition.step or 1)))
                field.setValue(int(definition.coerce(definition.default)))
                field.setSuffix(definition.suffix)
            else:
                field = QDoubleSpinBox()
                field.setDecimals(3)
                field.setRange(
                    float(definition.minimum if definition.minimum is not None else -9999),
                    float(definition.maximum if definition.maximum is not None else 9999),
                )
                field.setSingleStep(float(definition.step or 0.1))
                field.setValue(float(definition.coerce(definition.default)))
                field.setSuffix(definition.suffix)
            parameter_id = definition.parameter_id if definition else str(param)
            field.setProperty("parameter_id", parameter_id)
            label.setProperty("parameter_id", parameter_id)
            field.setToolTip(definition.tooltip if definition else "")
            field.setFocusPolicy(Qt.StrongFocus)
            field.setStyleSheet(
                "background-color: #172033; color: white; padding: 2px;"
            )

            form_layout.addRow(label, field)

        param_block.addLayout(form_layout)

        wrapper = QWidget()
        wrapper.setLayout(param_block)
        # Keep the stable UI object name. The visible label (for example
        # "Campfire") does not contain the main_/sub_ prefix.
        wrapper.setProperty("effect_key", button_name)
        wrapper.setProperty("effect_block", True)
        if is_sub:
            wrapper.setEnabled(False)
            wrapper.setToolTip(
                "Preserved for compatibility; no renderer is connected to this setting"
            )
        wrapper.setStyleSheet("background-color: rgba(255, 255, 255, 0.05); border-radius: 6px; padding: 4px;")

        shape_card.frame_layout.addWidget(wrapper)

    def collect_shape_cards_data(self):
        shape_cards_data = []

        for shape_id, graphics_widget in self.shape_cards.items():
            proxy = graphics_widget.layout().itemAt(0)
            shape_card = proxy.widget() if proxy else None
            if not shape_card:
                continue

            shape_info = {
                "id": shape_id,
                "tool_type": shape_card.tool_type,
                "main": None,
                "sub": [],
                "panel_position": {
                    "x": round(float(graphics_widget.pos().x()), 2),
                    "y": round(float(graphics_widget.pos().y()), 2),
                },
            }
            if shape_card.motion_controls.configured:
                shape_info["motion"] = shape_card.motion_data()

            for i in range(shape_card.frame_layout.count()):
                block = shape_card.frame_layout.itemAt(i).widget()
                if not block or not bool(block.property("effect_block")):
                    continue

                layout = block.layout()
                if layout is None or layout.count() == 0:
                    continue

                function_label = layout.itemAt(0).widget().text()
                function_key = str(block.property("effect_key") or function_label)
                form_layout = layout.itemAt(1)
                if not isinstance(form_layout, QFormLayout):
                    continue

                params = {}
                for row in range(form_layout.rowCount()):
                    label = form_layout.itemAt(row, QFormLayout.LabelRole).widget()
                    field = form_layout.itemAt(row, QFormLayout.FieldRole).widget()
                    if not label or not field:
                        continue
                    parameter_id = str(
                        field.property("parameter_id") or label.text()
                    )
                    if hasattr(field, "selected"):
                        params[parameter_id] = field.selected
                    elif isinstance(field, (QSpinBox, QDoubleSpinBox)):
                        params[parameter_id] = field.value()

                function_data = {"key": function_key, "name": function_label, "params": params}
                if function_key.lower().startswith("main_"):
                    shape_info["main"] = function_data
                else:
                    shape_info["sub"].append(function_data)

            try:
                from effect_engine.preset_registry import preset_id_from_card

                preset_id = preset_id_from_card(shape_info, shape_card.tool_type)
            except (KeyError, ValueError):
                preset_id = None
            if preset_id is not None:
                shape_info["preset_id"] = preset_id
            shape_cards_data.append(shape_info)

        return shape_cards_data

    def save_effects_to_project(self):
        """Atomically update only AI effect cards in the current project file."""
        shapes_json = self.render_shapes_json_path
        if not shapes_json or not os.path.isfile(shapes_json):
            shapes_json, _ = QFileDialog.getOpenFileName(
                self,
                "Select shapes.json",
                "",
                "JSON (*.json)",
            )
            if not shapes_json:
                return None

        temp_path = None
        try:
            with open(shapes_json, "r", encoding="utf-8") as source:
                project = json.load(source)
            if not isinstance(project, dict):
                raise ValueError("shapes.json должен содержать JSON-объект")

            valid_ids = set()
            for shape in project.get("shapes") or []:
                try:
                    valid_ids.add(int(shape.get("id")))
                except (AttributeError, TypeError, ValueError):
                    continue

            cards = []
            for card in self.collect_shape_cards_data():
                try:
                    card_id = int(card.get("id"))
                except (AttributeError, TypeError, ValueError):
                    continue
                if card_id in valid_ids:
                    cards.append(card)
            project["shape_cards"] = cards

            flow_directions = project.get("flow_directions")
            if not isinstance(flow_directions, dict):
                flow_directions = {}
            from effect_engine.project import normalize_direction
            for card in cards:
                motion = card.get("motion")
                if not isinstance(motion, dict):
                    continue
                direction = normalize_direction(motion.get("direction"))
                if direction is None:
                    continue
                key = str(int(card["id"]))
                existing = normalize_direction(flow_directions.get(key))
                if existing is None or any(
                    abs(existing[index] - direction[index]) > 1e-7
                    for index in (0, 1)
                ):
                    flow_directions[key] = {"x": direction[0], "y": direction[1]}
            project["flow_directions"] = flow_directions

            project_dir = os.path.dirname(os.path.abspath(shapes_json))
            with tempfile.NamedTemporaryFile(
                "w",
                encoding="utf-8",
                dir=project_dir,
                prefix=".shapes-",
                suffix=".tmp",
                delete=False,
            ) as temp_file:
                temp_path = temp_file.name
                json.dump(project, temp_file, ensure_ascii=False, indent=4)
                temp_file.write("\n")
            os.replace(temp_path, shapes_json)
            temp_path = None
        except Exception as error:
            if temp_path and os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except OSError:
                    pass
            self._set_render_status("Save effects: ошибка", 8000)
            QMessageBox.critical(
                self,
                "Save effects",
                f"Не удалось сохранить настройки эффектов:\n{error}",
            )
            return None

        self.render_shapes_json_path = shapes_json
        self._set_render_status(
            f"Save effects: сохранено {len(cards)} карточек",
            8000,
        )
        QMessageBox.information(
            self,
            "Save effects",
            f"Настройки эффектов сохранены:\n{shapes_json}",
        )
        return shapes_json

    # ---------------------------
    # Render button logic
    # ---------------------------
    def set_render_sources(self, shapes_json_path: str = None, masks_dir: str = None, pieces_dir: str = None,
                           out_mp4_path: str = None):
        """
        Позволяет главному окну передать пути проекта, чтобы render работал без диалогов.
        shapes_json_path: путь к shapes.json
        masks_dir: папка где лежат shape_<id>.svg
        pieces_dir: папка где лежат shape_<id>.png
        out_mp4_path: куда сохранить mp4
        """
        if shapes_json_path:
            self.render_shapes_json_path = shapes_json_path
            self._load_project_motion(shapes_json_path)
        if masks_dir:
            self.render_masks_dir = masks_dir
        if pieces_dir:
            self.render_pieces_dir = pieces_dir
        if out_mp4_path:
            self.render_out_mp4_path = out_mp4_path

    def _load_project_motion(self, shapes_json_path):
        """Populate controls from card motion or legacy top-level flow vectors."""
        try:
            with open(shapes_json_path, "r", encoding="utf-8") as source:
                project = json.load(source)
        except (OSError, ValueError):
            return

        cards_by_id = {}
        for card in project.get("shape_cards") or []:
            try:
                cards_by_id[int(card.get("id"))] = card
            except (AttributeError, TypeError, ValueError):
                continue
        directions = project.get("flow_directions") or {}
        if not isinstance(directions, dict):
            directions = {}
        for shape_id, graphics_widget in self.shape_cards.items():
            proxy = graphics_widget.layout().itemAt(0)
            shape_card = proxy.widget() if proxy else None
            if shape_card is None or shape_card.motion_controls.configured:
                continue
            saved_motion = (cards_by_id.get(int(shape_id)) or {}).get("motion")
            if isinstance(saved_motion, dict):
                shape_card.set_motion(saved_motion, configured=True)
                continue
            raw_direction = directions.get(str(int(shape_id)), directions.get(int(shape_id)))
            if raw_direction is not None:
                self.set_shape_direction(shape_id, raw_direction)

    def on_render_clicked(self):
        if self._svd_job_id:
            self._request_svd_cancel()
            return

        sync_callback = getattr(self, "project_sync_callback", None)
        if callable(sync_callback):
            try:
                synced_path = sync_callback()
            except Exception as error:
                self._set_render_status("AI render: project sync failed", 8000)
                QMessageBox.critical(
                    self,
                    "Project sync error",
                    f"Could not save the current project before rendering:\n{error}",
                )
                return
            if synced_path:
                self.render_shapes_json_path = synced_path

        # 1) определяем shapes.json
        shapes_json = self.render_shapes_json_path
        if not shapes_json:
            shapes_json, _ = QFileDialog.getOpenFileName(self, "Select shapes.json", "", "JSON (*.json)")
            if not shapes_json:
                return
            self.render_shapes_json_path = shapes_json
        if not os.path.isfile(shapes_json):
            QMessageBox.critical(
                self,
                "Project error",
                f"Файл проекта не найден:\n{shapes_json}",
            )
            return

        base_dir = os.path.dirname(shapes_json)

        # 2) определяем masks/pieces
        masks_dir = self.render_masks_dir
        if not masks_dir:
            masks_dir = _find_first_existing(os.path.join(base_dir, "masks")) or base_dir
            self.render_masks_dir = masks_dir

        pieces_dir = self.render_pieces_dir
        if not pieces_dir:
            pieces_dir = _find_first_existing(os.path.join(base_dir, "pieces")) or base_dir
            self.render_pieces_dir = pieces_dir

        # 3) выход
        out_mp4 = self.render_out_mp4_path
        if not out_mp4:
            out_mp4 = os.path.join(base_dir, "result.mp4")
            self.render_out_mp4_path = out_mp4

        # Запускаем удалённый GPU-рендер через backend.
        self._start_remote_render(shapes_json, out_mp4, masks_dir, pieces_dir)


    # ---------------------------
    # Remote render via backend
    # ---------------------------
    def _start_remote_render(self, shapes_json: str, out_mp4: str, masks_dir: str, pieces_dir: str):
        """Стартуем SVD-рендер на backend и начинаем опрос статуса."""
        if self._svd_job_id:
            QMessageBox.information(self, "AI render", "AI render уже выполняется.")
            return
        if hasattr(self.ui, "pushButton"):
            self.ui.pushButton.setEnabled(False)
        self._svd_started_at = time.monotonic()
        self._last_svd_progress_key = None
        if hasattr(self, "render_progress_bar"):
            self.render_progress_bar.setRange(0, 0)
            self.render_progress_bar.setFormat("Проверка backend...")
            self.render_progress_bar.show()
        self._set_render_status("AI render: проверка backend...")

        from backend_async import run_in_thread
        import backend_client
        import os

        try:
            print(f"[DEBUG] backend_client={backend_client.__file__}")
            print(f"[DEBUG] BASE={getattr(backend_client,'BASE',None)}")
            print(f"[DEBUG] shapes_json={shapes_json} exists={os.path.exists(shapes_json)}")
            print(f"[DEBUG] out_mp4={out_mp4}")
        except Exception:
            pass

        def _ok(res: object):
            job_id = res if isinstance(res, str) else (res.get("job_id") if isinstance(res, dict) else None)
            if not job_id:
                if hasattr(self.ui, "pushButton"):
                    self.ui.pushButton.setEnabled(True)
                try:
                    print(f"[DEBUG] [RENDER] unexpected response: {res}")
                except Exception:
                    pass
                self._set_render_status("AI render: некорректный ответ", 8000)
                QMessageBox.critical(self, "Render error", f"Backend вернул неожиданный ответ: {res}")
                return

            self._svd_job_id = str(job_id)
            self._svd_status_failures = 0
            self._svd_poll_in_flight = False
            if hasattr(self, "render_progress_bar"):
                self.render_progress_bar.setRange(0, 0)
                self.render_progress_bar.setFormat("В очереди...")
            self._set_render_status("AI: задание поставлено в очередь")
            if hasattr(self.ui, "pushButton"):
                self.ui.pushButton.setEnabled(True)
                self.ui.pushButton.setText("Cancel render")
            try:
                print(f"[DEBUG] [RENDER] job_id={self._svd_job_id}")
            except Exception:
                pass
            self._svd_timer.start(2000)

        def _err(msg: str):
            if hasattr(self.ui, "pushButton"):
                self.ui.pushButton.setEnabled(True)
            self._svd_job_id = None
            self._svd_started_at = None
            if hasattr(self, "render_progress_bar"):
                self.render_progress_bar.hide()
            self._set_render_status("AI render: backend не готов", 8000)
            try:
                print(f"[DEBUG] [RENDER] error: {msg}")
            except Exception:
                pass
            QMessageBox.warning(self, "AI render недоступен", str(msg))

        run_in_thread(
            self,
            backend_client.start_svd_render_checked,
            _ok,
            _err,
            shapes_json,
            out_mp4,
            masks_dir=masks_dir,
            pieces_dir=pieces_dir,
            timeout=30.0,
        )

    def _request_svd_cancel(self):
        job_id = self._svd_job_id
        if not job_id:
            return
        from backend_async import run_in_thread
        import backend_client

        if hasattr(self.ui, "pushButton"):
            self.ui.pushButton.setEnabled(False)
            self.ui.pushButton.setText("Cancelling...")
        self._set_render_status("AI render: cancelling...")

        def on_ok(_result):
            if self._svd_job_id == job_id:
                self._set_render_status("AI render: cancellation requested")
                self._svd_timer.setInterval(1000)
                self._svd_timer.start()

        def on_error(message):
            if self._svd_job_id != job_id:
                return
            if hasattr(self.ui, "pushButton"):
                self.ui.pushButton.setEnabled(True)
                self.ui.pushButton.setText("Cancel render")
            self._set_render_status("AI render: cancellation failed", 8000)
            QMessageBox.warning(self, "Cancel render", str(message))

        run_in_thread(
            self,
            backend_client.cancel_svd_render,
            on_ok,
            on_error,
            job_id,
            timeout=5.0,
        )

    def _poll_svd_status(self):
        """Poll status outside the UI thread so a slow backend cannot freeze Qt."""
        job_id = getattr(self, "_svd_job_id", None)
        if not job_id or self._svd_poll_in_flight:
            return

        from backend_async import run_in_thread
        import backend_client

        self._svd_poll_in_flight = True

        def on_status(status: object) -> None:
            self._svd_poll_in_flight = False
            if self._svd_job_id != job_id:
                return
            if not isinstance(status, dict):
                self._on_svd_status_error("Backend вернул некорректный статус")
                return
            self._handle_svd_status(status)

        def on_error(message: str) -> None:
            self._svd_poll_in_flight = False
            if self._svd_job_id == job_id:
                self._on_svd_status_error(message)

        run_in_thread(
            self,
            backend_client.get_svd_status,
            on_status,
            on_error,
            job_id,
            timeout=3.0,
        )

    def _on_svd_status_error(self, message: str) -> None:
        self._svd_status_failures += 1
        failure_limit = 3
        print(
            f"[DEBUG] [RENDER] status error "
            f"{self._svd_status_failures}/{failure_limit}: {message}"
        )
        if self._svd_status_failures < failure_limit:
            self._set_render_status(
                f"AI render: потеряна связь, повтор "
                f"{self._svd_status_failures}/{failure_limit}"
            )
            return

        self._svd_timer.setInterval(10000)
        if hasattr(self.ui, "pushButton"):
            self.ui.pushButton.setEnabled(True)
            self.ui.pushButton.setText("Cancel render")
        self._set_render_status(
            "AI render: connection lost; reconnecting every 10 seconds"
        )

    def _handle_svd_status(self, status: dict) -> None:
        self._svd_status_failures = 0
        self._svd_timer.setInterval(2000)
        state = str(status.get("state") or "unknown")
        prog = status.get("progress") or {}
        stage = str(prog.get("stage") or "")
        step = prog.get("step")
        steps = prog.get("steps")
        current = prog.get("current")
        total = prog.get("total")
        elapsed = (
            max(0, int(time.monotonic() - self._svd_started_at))
            if self._svd_started_at is not None
            else 0
        )
        elapsed_text = f"{elapsed // 60:02d}:{elapsed % 60:02d}"
        stage_labels = {
            "queued": "в очереди",
            "loading_pipeline": "загрузка AI-модели",
            "rendering": "генерация кадров",
            "decoding": "декодирование кадров",
            "postprocessing": "постобработка",
            "interpolating": "сглаживание движения",
            "encoding": "сохранение MP4",
            "done": "готово",
        }
        base_stage_text = stage_labels.get(stage, stage or state)
        stage_text = base_stage_text
        if step is not None and steps:
            stage_text += f" {step}/{steps}"
        if current is not None and total and int(total) > 1:
            unit = "кадр" if stage in {"interpolating", "encoding"} else "слой"
            stage_text += f" • {unit} {current}/{total}"
        status_text = f"AI: {stage_text} • {elapsed_text}"
        self._set_render_status(status_text)

        if hasattr(self, "render_progress_bar"):
            self.render_progress_bar.show()
            if step is not None and steps:
                self.render_progress_bar.setRange(0, int(steps))
                self.render_progress_bar.setValue(int(step))
                self.render_progress_bar.setFormat(f"{base_stage_text} — %v/%m")
            elif current is not None and total and int(total) > 1:
                self.render_progress_bar.setRange(0, int(total))
                self.render_progress_bar.setValue(int(current))
                self.render_progress_bar.setFormat(f"{base_stage_text} — %v/%m")
            else:
                self.render_progress_bar.setRange(0, 0)
                self.render_progress_bar.setFormat(stage_text)

        progress_key = (state, stage, step, steps, current, total)
        if progress_key != self._last_svd_progress_key:
            print(f"[AI RENDER] {status_text}")
            self._last_svd_progress_key = progress_key

        if state == "done":
            self._svd_timer.stop()
            self._svd_job_id = None
            self._svd_started_at = None
            if hasattr(self.ui, "pushButton"):
                self.ui.pushButton.setEnabled(True)
                self.ui.pushButton.setText("AI render")
            result = status.get("result") or {}
            output_path = (
                result.get("out_mp4_win")
                or result.get("out_mp4")
                or result.get("out_mp4_wsl")
                or ""
            )
            try:
                print(f"[DEBUG] [RENDER] done output={output_path}")
            except Exception:
                pass
            self._set_render_status("AI render: готово", 8000)
            if hasattr(self, "render_progress_bar"):
                self.render_progress_bar.setRange(0, 1)
                self.render_progress_bar.setValue(1)
                self.render_progress_bar.setFormat("Готово")
            QMessageBox.information(self, "Render", f"Saved:\n{output_path}")
            return

        if state == "error":
            self._svd_timer.stop()
            self._svd_job_id = None
            self._svd_started_at = None
            if hasattr(self.ui, "pushButton"):
                self.ui.pushButton.setEnabled(True)
                self.ui.pushButton.setText("AI render")
            err = status.get("error") or "unknown error"
            try:
                print(f"[DEBUG] [RENDER] error state: {err}")
            except Exception:
                pass
            self._set_render_status("AI render: ошибка", 8000)
            if hasattr(self, "render_progress_bar"):
                self.render_progress_bar.hide()
            QMessageBox.critical(self, "Render error", str(err))
            return

        if state == "cancelled":
            self._svd_timer.stop()
            self._svd_job_id = None
            self._svd_started_at = None
            if hasattr(self.ui, "pushButton"):
                self.ui.pushButton.setEnabled(True)
                self.ui.pushButton.setText("AI render")
            if hasattr(self, "render_progress_bar"):
                self.render_progress_bar.hide()
            self._set_render_status("AI render: cancelled", 8000)

    def _start_render_thread(self, shapes_json: str, out_mp4: str, masks_dir: str, pieces_dir: str):
        if hasattr(self.ui, "pushButton"):
            self.ui.pushButton.setEnabled(False)
        self._set_render_status("render: starting...")

        self._render_thread = QThread(self)
        self._render_worker = RenderWorker(shapes_json, out_mp4, masks_dir, pieces_dir)
        self._render_worker.moveToThread(self._render_thread)

        self._render_thread.started.connect(self._render_worker.run)
        self._render_worker.progress.connect(self._on_render_progress)
        self._render_worker.finished.connect(self._on_render_finished)
        self._render_worker.error.connect(self._on_render_error)

        self._render_worker.finished.connect(self._render_thread.quit)
        self._render_worker.error.connect(self._render_thread.quit)
        self._render_thread.finished.connect(self._cleanup_render_thread)

        self._render_thread.start()

    def _on_render_progress(self, text: str):
        self._set_render_status("render: " + text)

    def _on_render_finished(self, out_path: str):
        self._set_render_status("render: done", 8000)
        if hasattr(self.ui, "pushButton"):
            self.ui.pushButton.setEnabled(True)
        QMessageBox.information(self, "Render", f"Saved: {out_path}")

    def _on_render_error(self, msg: str):
        self._set_render_status("render: error", 8000)
        if hasattr(self.ui, "pushButton"):
            self.ui.pushButton.setEnabled(True)
        QMessageBox.critical(self, "Render error", msg)

    def _cleanup_render_thread(self):
        # аккуратно освобождаем ссылки
        self._render_worker = None
        self._render_thread = None
