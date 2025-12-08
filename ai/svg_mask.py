import numpy as np
from PIL import Image, ImageFilter

from PySide6.QtCore import Qt
from PySide6.QtGui import QImage, QPainter
from PySide6.QtSvg import QSvgRenderer


def rasterize_svg_to_mask(svg_path: str, width: int, height: int, feather_px: int = 5) -> Image.Image:
    """
    Рендерит SVG в QImage и возвращает PIL L-маску (0..255).
    В SVG желательно иметь заливку (fill) внутри формы.
    """
    renderer = QSvgRenderer(svg_path)

    img = QImage(width, height, QImage.Format_ARGB32_Premultiplied)
    img.fill(Qt.transparent)

    p = QPainter(img)
    renderer.render(p)  # растянет SVG на весь img (учитывает viewBox)
    p.end()

    # QImage -> numpy (BGRA), учитываем bytesPerLine
    ptr = img.bits()
    ptr.setsize(img.sizeInBytes())
    arr = np.frombuffer(ptr, np.uint8).reshape((height, img.bytesPerLine() // 4, 4))
    arr = arr[:, :width, :]  # обрезаем padding по строкам

    alpha = arr[..., 3]  # 0..255
    mask = Image.fromarray(alpha, mode="L")

    if feather_px and feather_px > 0:
        mask = mask.filter(ImageFilter.GaussianBlur(radius=feather_px))
    return mask
