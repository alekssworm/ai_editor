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
    cycles: int = 1
    advection: float = 0.6
    cross_flow: float = 0.7
    shimmer: float = 0.04

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
            cycles=max(1, min(8, int(values.get("cycles", defaults.cycles)))),
            advection=float(
                np.clip(values.get("advection", defaults.advection), 0.0, 1.5)
            ),
            cross_flow=float(
                np.clip(values.get("cross_flow", defaults.cross_flow), 0.0, 1.5)
            ),
            shimmer=float(
                np.clip(values.get("shimmer", defaults.shimmer), 0.0, 0.25)
            ),
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
        phase = np.float32(np.pi * 2.0 * (float(t) % 1.0) * config.cycles)
        rng = np.random.default_rng(assets.seed)
        phase_a, phase_b = rng.uniform(0.0, np.pi * 2.0, size=2).astype(np.float32)
        frequency_scale = np.float32(rng.uniform(0.9, 1.1))

        height, width = assets.mask.shape
        y, x = np.mgrid[0:height, 0:width].astype(np.float32)
        raw_flow_x = assets.flow[..., 0]
        raw_flow_y = assets.flow[..., 1]
        flow_speed = np.clip(
            np.hypot(raw_flow_x, raw_flow_y), 0.0, 1.0
        ).astype(np.float32)
        safe_length = np.maximum(flow_speed, 1e-6)
        flow_x = raw_flow_x / safe_length
        flow_y = raw_flow_y / safe_length
        style_scale = np.float32(
            np.clip(
                0.85 + assets.style.edge_softness * 0.25 - assets.style.grain * 0.1,
                0.7,
                1.15,
            )
        )
        along = x * flow_x + y * flow_y
        across = -x * flow_y + y * flow_x

        wave_a = np.sin(
            along * (np.pi * 2.0 / config.wavelength) * frequency_scale - phase + phase_a
        )
        wave_b = np.sin(
            across * (np.pi * 2.0 / config.secondary_wavelength) - phase * 2.0 + phase_b
        )

        depth_scale = 0.65 + assets.depth * 0.7
        amplitude = (
            np.float32(config.strength)
            * depth_scale
            * style_scale
            * (0.15 + flow_speed * 0.85)
        )
        displacement_along = amplitude * (0.2 + config.advection * 0.45) * wave_a
        displacement_across = amplitude * config.cross_flow * wave_b
        dx = flow_x * displacement_along - flow_y * displacement_across
        dy = flow_y * displacement_along + flow_x * displacement_across

        warped = _bilinear_remap(rgb, x + dx, y + dy)
        if config.shimmer > 0:
            shimmer = (
                wave_a
                * wave_b
                * np.float32(config.shimmer * 10.0)
                * (0.6 + assets.style.contrast * 0.4)
            )
            warped = np.clip(warped + shimmer[..., None], 0.0, 255.0)
        alpha = np.clip(assets.mask * config.opacity, 0.0, 1.0)[..., None]
        composed = warped * alpha + rgb * (1.0 - alpha)
        return Image.fromarray(np.clip(np.rint(composed), 0, 255).astype(np.uint8), mode="RGB")
