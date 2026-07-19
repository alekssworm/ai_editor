from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

import numpy as np
from PIL import Image

from ..models import EffectAssets


def _reflect_coordinates(values: np.ndarray, size: int) -> np.ndarray:
    if size <= 1:
        return np.zeros_like(values, dtype=np.float32)
    maximum = float(size - 1)
    period = maximum * 2.0
    folded = np.mod(values, period)
    return np.where(folded <= maximum, folded, period - folded).astype(np.float32)


def _bilinear_remap(image: np.ndarray, map_x: np.ndarray, map_y: np.ndarray) -> np.ndarray:
    height, width = image.shape[:2]
    x = _reflect_coordinates(map_x, width)
    y = _reflect_coordinates(map_y, height)

    x0 = np.floor(x).astype(np.int32)
    y0 = np.floor(y).astype(np.int32)
    x1 = np.minimum(x0 + 1, width - 1)
    y1 = np.minimum(y0 + 1, height - 1)

    wx = (x - x0)[..., None]
    wy = (y - y0)[..., None]

    top = image[y0, x0] * (1.0 - wx) + image[y0, x1] * wx
    bottom = image[y1, x0] * (1.0 - wx) + image[y1, x1] * wx
    return top * (1.0 - wy) + bottom * wy


@dataclass(frozen=True, slots=True)
class WaterFlowParams:
    strength: float = 4.0
    wavelength: float = 56.0
    secondary_wavelength: float = 31.0
    opacity: float = 1.0

    @classmethod
    def from_mapping(cls, values: Mapping[str, float] | None) -> "WaterFlowParams":
        values = values or {}
        defaults = cls()
        return cls(
            strength=float(values.get("strength", defaults.strength)),
            wavelength=max(4.0, float(values.get("wavelength", defaults.wavelength))),
            secondary_wavelength=max(
                4.0,
                float(values.get("secondary_wavelength", defaults.secondary_wavelength)),
            ),
            opacity=float(np.clip(values.get("opacity", defaults.opacity), 0.0, 1.0)),
        )


class WaterFlowEffect:
    effect_type = "water"

    def render(
        self,
        image: Image.Image | np.ndarray,
        assets: EffectAssets,
        t: float,
        params: Mapping[str, float] | None = None,
    ) -> Image.Image:
        config = WaterFlowParams.from_mapping(params)
        if isinstance(image, Image.Image):
            rgb = np.asarray(image.convert("RGB"), dtype=np.float32)
        else:
            rgb = np.asarray(image, dtype=np.float32)[..., :3]
        if rgb.shape[:2] != assets.mask.shape:
            raise ValueError(f"image shape {rgb.shape[:2]} does not match assets {assets.mask.shape}")

        # Modulo makes t=1 exactly equal to t=0 instead of relying on sin(2*pi)
        # floating-point rounding.
        phase = np.float32(np.pi * 2.0 * (float(t) % 1.0))
        rng = np.random.default_rng(assets.seed)
        phase_a, phase_b = rng.uniform(0.0, np.pi * 2.0, size=2).astype(np.float32)
        frequency_scale = np.float32(rng.uniform(0.9, 1.1))

        height, width = assets.mask.shape
        y, x = np.mgrid[0:height, 0:width].astype(np.float32)
        flow_x = assets.flow[..., 0]
        flow_y = assets.flow[..., 1]
        along = x * flow_x + y * flow_y
        across = -x * flow_y + y * flow_x

        wave_a = np.sin(
            along * (np.pi * 2.0 / config.wavelength) * frequency_scale - phase + phase_a
        )
        wave_b = np.sin(
            across * (np.pi * 2.0 / config.secondary_wavelength) - phase * 2.0 + phase_b
        )

        depth_scale = 0.65 + assets.depth * 0.7
        amplitude = np.float32(config.strength) * depth_scale
        displacement_along = amplitude * 0.45 * wave_a
        displacement_across = amplitude * wave_b
        dx = flow_x * displacement_along - flow_y * displacement_across
        dy = flow_y * displacement_along + flow_x * displacement_across

        warped = _bilinear_remap(rgb, x + dx, y + dy)
        alpha = np.clip(assets.mask * config.opacity, 0.0, 1.0)[..., None]
        composed = warped * alpha + rgb * (1.0 - alpha)
        return Image.fromarray(np.clip(np.rint(composed), 0, 255).astype(np.uint8), mode="RGB")
