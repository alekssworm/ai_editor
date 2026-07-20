import json
import math
import os
import traceback
from typing import Optional, Tuple, Callable

from PySide6.QtCore import QStringListModel, QThread, QObject, Signal, Qt, QTimer
from PySide6.QtGui import QFont, QFontMetrics
from PySide6.QtGui import QPainter
from PySide6.QtWidgets import (
    QMainWindow, QGraphicsScene, QGraphicsView, QLabel, QFrame, QSizePolicy, QFormLayout, QFileDialog, QMessageBox
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




class ShapeCard(QWidget):
    def __init__(self, shape_id, shape_type, color_name):
        super().__init__()
        self.shape_id = shape_id
        self.setFocusPolicy(Qt.NoFocus)


        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(4, 4, 4, 4)
        self.main_layout.setSpacing(4)

        label = QLabel(f"{shape_type} | ID: {shape_id}")
        label.setStyleSheet(f"""
            color: white;
            border: 2px solid {color_name};
            padding: 2px;
        """)
        label.setFocusPolicy(Qt.NoFocus)
        self.main_layout.addWidget(label)

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

        self.tool_type = None
        self.main_function_added = False
        self.added_subfunctions = set()


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
    def __init__(self):
        super().__init__()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self.selected_shape_id = None
        if hasattr(self.ui, "pushButton"):
            self.ui.pushButton.setText("AI render (WSL)")
            self.ui.pushButton.setToolTip(
                "Stable Video Diffusion render; requires backend_server.py in WSL"
            )

        self.scene = QGraphicsScene(self)
        self.ui.graphicsView.setRenderHint(QPainter.Antialiasing)
        self.ui.graphicsView.setScene(self.scene)
        self.ui.graphicsView.setDragMode(QGraphicsView.NoDrag)
        self.ui.graphicsView.setStyleSheet("background-color: #1e1e1e; border: none;")
        self.ui.graphicsView.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.ui.graphicsView.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)

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
        self._svd_timer = QTimer(self)
        self._svd_timer.timeout.connect(self._poll_svd_status)


        self.shape_cards = {}
        self.last_tool_type = None

        self.tool_container_layout = QVBoxLayout(self.ui.scrollAreaWidgetContents)
        self.tool_container_layout.setSpacing(6)
        self.tool_container_layout.setContentsMargins(4, 4, 4, 4)

    def add_shape_card(self, shape_id, shape_type, color_name):
        shape_widget = ShapeCard(shape_id, shape_type, color_name)
        widget = ShapeCardGraphicsWidget(shape_id, shape_widget, self)
        widget.setPos(40 + len(self.shape_cards) * 30, 40 + len(self.shape_cards) * 30)
        self.scene.addItem(widget)
        self.shape_cards[shape_id] = widget

        print(f"[DEBUG] ShapeCard created: ID = {shape_id}")

    def select_shape_card(self, shape_id) -> None:
        self.selected_shape_id = int(shape_id)
        if hasattr(self.ui, "label_14"):
            self.ui.label_14.setText(str(self.selected_shape_id))

    def _set_render_status(self, text: str, timeout: int = 0) -> None:
        self.statusBar().showMessage(str(text), int(timeout))

    def clear_shape_cards(self):
        """Reset cards when a new image or project replaces the current scene."""
        self.scene.clear()
        self.shape_cards.clear()
        self.last_tool_type = None
        self.selected_shape_id = None
        if hasattr(self.ui, "label_14"):
            self.ui.label_14.clear()

    def reset_project_state(self):
        self.clear_shape_cards()
        self.render_shapes_json_path = None
        self.render_masks_dir = None
        self.render_pieces_dir = None
        self.render_out_mp4_path = None
        self._svd_job_id = None
        self._svd_poll_in_flight = False
        self._svd_status_failures = 0
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

            proxy = graphics_widget.layout().itemAt(0)
            shape_card = proxy.widget() if proxy else None
            if shape_card is None:
                continue

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
                self.add_button_name_to_shape_card(display_name, effect_key)
                if shape_card.frame_layout.count() == count_before:
                    continue

                block = shape_card.frame_layout.itemAt(shape_card.frame_layout.count() - 1).widget()
                form_layout = block.layout().itemAt(1) if block and block.layout() else None
                saved_params = entry.get("params") or {}
                if not isinstance(form_layout, QFormLayout) or not isinstance(saved_params, dict):
                    continue
                for row in range(form_layout.rowCount()):
                    label = form_layout.itemAt(row, QFormLayout.LabelRole).widget()
                    combo = form_layout.itemAt(row, QFormLayout.FieldRole).widget()
                    if label and combo and label.text() in saved_params:
                        combo.setCurrentText(str(saved_params[label.text()]))

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

        tool_widget = QWidget()
        ui = ui_class()
        ui.setupUi(tool_widget)

        if ui_class is Ui_water_tool:
            from effect_engine.preset_registry import default_preset_registry

            existing_keys = {
                button.objectName().casefold()
                for button in tool_widget.findChildren(QPushButton)
            }
            for preset in default_preset_registry().list("water"):
                editor_key = preset.editor_key or f"main_{preset.preset_id}"
                if editor_key.casefold() in existing_keys:
                    continue
                button = QPushButton(preset.label, ui.splitter_347)
                button.setObjectName(editor_key)
                ui.splitter_347.addWidget(button)
                existing_keys.add(editor_key.casefold())

        buttons = tool_widget.findChildren(QPushButton)
        print(f"[DEBUG] Найдено {len(buttons)} кнопок в {ui_class.__name__}")

        for btn in buttons:
            btn_text = btn.text().strip()
            btn_name = btn.objectName().strip()
            if (
                btn_text
                and btn_text.casefold() not in {"x", "color"}
                and btn_name.casefold() not in {"x", "color"}
            ):
                btn.clicked.connect(lambda _, text=btn_text, name=btn_name: self.add_button_name_to_shape_card(text, name))
                print(f"[DEBUG] Привязан обработчик к кнопке: {btn_text} ({btn_name})")

        tool_widget._tool_class = ui_class
        size_policy = QSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        tool_widget.setSizePolicy(size_policy)
        self.tool_container_layout.addWidget(tool_widget)

    def add_button_name_to_shape_card(self, button_text, button_name):
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

        tool_type = self.last_tool_type.lower().replace('ui_', '').replace('_tool', '')
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
        label.setStyleSheet("color: white; font-weight: bold;")
        param_block.addWidget(label)

        params = TOOL_PARAMETERS.get(f"{tool_type}:{button_name}", TOOL_PARAMETERS.get(button_name, []))
        if is_main and not params:
            try:
                from effect_engine.preset_registry import default_preset_registry

                preset = default_preset_registry().resolve(tool_type, button_name)
                params = list(preset.controls)
            except KeyError:
                pass
        from PySide6.QtWidgets import QFormLayout  # обязательно добавить в импорты

        form_layout = QFormLayout()
        form_layout.setSpacing(6)
        form_layout.setContentsMargins(0, 0, 0, 0)

        font = QFont()
        font.setPointSize(12)
        metrics = QFontMetrics(font)
        max_width = max((metrics.horizontalAdvance(p) for p in params), default=0) + 10

        for param in params:
            label = QLabel(param)
            label.setWordWrap(False)
            label.setStyleSheet(f"""
                color: lightgray;
                font-size: 12px;
                min-width: {max_width}px;
                max-width: {max_width}px;
            """)

            combo = InSceneComboBox()
            combo.addItems(["none", "default", "weak", "normal", "strong"])
            combo.setCurrentText("default")
            combo.setFocusPolicy(Qt.StrongFocus)
            combo.setFocus()
            combo.setStyleSheet("background-color: #2a2a2a; color: white; padding: 2px;")

            form_layout.addRow(label, combo)

        param_block.addLayout(form_layout)

        wrapper = QWidget()
        wrapper.setLayout(param_block)
        # Keep the stable UI object name. The visible label (for example
        # "Campfire") does not contain the main_/sub_ prefix.
        wrapper.setProperty("effect_key", button_name)
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
            }

            for i in range(shape_card.frame_layout.count()):
                block = shape_card.frame_layout.itemAt(i).widget()
                if not block:
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
                    combo = form_layout.itemAt(row, QFormLayout.FieldRole).widget()
                    if label and combo and hasattr(combo, "selected"):
                        params[label.text()] = combo.selected

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
        if masks_dir:
            self.render_masks_dir = masks_dir
        if pieces_dir:
            self.render_pieces_dir = pieces_dir
        if out_mp4_path:
            self.render_out_mp4_path = out_mp4_path

    def on_render_clicked(self):
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

        # Запускаем удалённый рендер в WSL backend (CUDA на RTX 4070)
        self._start_remote_render(shapes_json, out_mp4, masks_dir, pieces_dir)


    # ---------------------------
    # Remote render via WSL backend
    # ---------------------------
    def _start_remote_render(self, shapes_json: str, out_mp4: str, masks_dir: str, pieces_dir: str):
        """Стартуем SVD-рендер на backend (WSL) и начинаем опрос статуса."""
        if self._svd_job_id:
            QMessageBox.information(self, "AI render", "AI render уже выполняется.")
            return
        if hasattr(self.ui, "pushButton"):
            self.ui.pushButton.setEnabled(False)
        self._set_render_status("AI render: проверка WSL backend...")

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
            self._set_render_status(f"AI render: queued ({self._svd_job_id})")
            try:
                print(f"[DEBUG] [RENDER] job_id={self._svd_job_id}")
            except Exception:
                pass
            self._svd_timer.start(1000)

        def _err(msg: str):
            if hasattr(self.ui, "pushButton"):
                self.ui.pushButton.setEnabled(True)
            self._svd_job_id = None
            self._set_render_status("AI render: backend недоступен", 8000)
            try:
                print(f"[DEBUG] [RENDER] error: {msg}")
            except Exception:
                pass
            QMessageBox.warning(self, "AI backend недоступен", str(msg))

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

        self._svd_timer.stop()
        self._svd_job_id = None
        if hasattr(self.ui, "pushButton"):
            self.ui.pushButton.setEnabled(True)
        self._set_render_status("AI render: соединение потеряно", 8000)
        QMessageBox.warning(self, "AI render", str(message))

    def _handle_svd_status(self, status: dict) -> None:
        self._svd_status_failures = 0
        state = str(status.get("state") or "unknown")
        prog = status.get("progress") or {}
        stage = prog.get("stage")
        stage_suffix = f" ({stage})" if stage else ""
        self._set_render_status(f"AI render: {state}{stage_suffix}")

        if state == "done":
            self._svd_timer.stop()
            self._svd_job_id = None
            if hasattr(self.ui, "pushButton"):
                self.ui.pushButton.setEnabled(True)
            result = status.get("result") or {}
            out_win = result.get("out_mp4_win") or result.get("out_mp4") or ""
            out_wsl = result.get("out_mp4_wsl") or ""
            try:
                print(f"[DEBUG] [RENDER] done out_win={out_win} out_wsl={out_wsl}")
            except Exception:
                pass
            self._set_render_status("AI render: готово", 8000)
            QMessageBox.information(self, "Render", f"Saved:\n{out_win or out_wsl}")
            return

        if state == "error":
            self._svd_timer.stop()
            self._svd_job_id = None
            if hasattr(self.ui, "pushButton"):
                self.ui.pushButton.setEnabled(True)
            err = status.get("error") or "unknown error"
            try:
                print(f"[DEBUG] [RENDER] error state: {err}")
            except Exception:
                pass
            self._set_render_status("AI render: ошибка", 8000)
            QMessageBox.critical(self, "Render error", str(err))

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
