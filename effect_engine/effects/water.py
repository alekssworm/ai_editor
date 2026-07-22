from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

import numpy as np

from ..context import EffectContext
from ..layers import EffectFrame, LayeredEffect
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
    highlight: float = 0.18
    foam_amount: float = 0.35
    turbulence: float = 0.25

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
            highlight=float(
                np.clip(values.get("highlight", defaults.highlight), 0.0, 1.0)
            ),
            foam_amount=float(
                np.clip(values.get("foam_amount", defaults.foam_amount), 0.0, 1.0)
            ),
            turbulence=float(
                np.clip(values.get("turbulence", defaults.turbulence), 0.0, 1.0)
            ),
        )


def _water_highlight_color(assets: EffectAssets) -> np.ndarray:
    colors = []
    for value in assets.style.palette:
        text = str(value).lstrip("#")
        if len(text) != 6:
            continue
        try:
            colors.append(np.array([int(text[i : i + 2], 16) for i in (0, 2, 4)]))
        except ValueError:
            continue
    if not colors:
        return np.array([205.0, 230.0, 242.0], dtype=np.float32)
    color = max(colors, key=lambda item: float(item @ np.array([0.21, 0.72, 0.07])))
    return (color.astype(np.float32) * 0.45 + 255.0 * 0.55).astype(np.float32)


class WaterWavesLayer:
    name = "waves"

    def apply(self, frame: EffectFrame, context: EffectContext) -> None:
        assets = context.assets
        config = WaterFlowParams.from_mapping(context.params)
        phase = np.float32(context.phase(config.cycles))
        rng = context.rng("water-waves")
        phase_a, phase_b, phase_c = rng.uniform(
            0.0, np.pi * 2.0, size=3
        ).astype(np.float32)
        frequency_scale = np.float32(rng.uniform(0.9, 1.1))

        height, width = assets.mask.shape
        y, x = np.mgrid[0:height, 0:width].astype(np.float32)
        flow_x = assets.flow[..., 0]
        flow_y = assets.flow[..., 1]
        flow_speed = np.asarray(assets.speed, dtype=np.float32)
        mobility = np.clip(1.0 - assets.obstacles, 0.0, 1.0)
        style_scale = np.float32(
            np.clip(
                0.85 + assets.style.edge_softness * 0.25 - assets.style.grain * 0.1,
                0.7,
                1.15,
            )
        )
        along = x * flow_x + y * flow_y
        across = -x * flow_y + y * flow_x

        # Temporal multipliers stay integer so t=1 wraps exactly to t=0.
        # Local speed changes wavelength/amplitude instead of breaking the loop.
        local_phase = phase
        spatial_speed = 0.72 + flow_speed * 0.56
        wave_a = np.sin(
            along
            * (np.pi * 2.0 / config.wavelength)
            * frequency_scale
            * spatial_speed
            - local_phase
            + phase_a
        )
        wave_b = np.sin(
            across
            * (np.pi * 2.0 / config.secondary_wavelength)
            * spatial_speed
            - local_phase * 2.0
            + phase_b
        )
        wave_c = np.sin(
            (along + across * 0.38)
            * (np.pi * 2.0 / max(8.0, config.wavelength * 0.46))
            - local_phase * 3.0
            + phase_c
        )

        frame.data["water"] = {
            "config": config,
            "x": x,
            "y": y,
            "along": along,
            "flow_x": flow_x,
            "flow_y": flow_y,
            "flow_speed": flow_speed,
            "mobility": mobility,
            "style_scale": style_scale,
            "phase": phase,
            "phase_c": phase_c,
            "wave_a": wave_a,
            "wave_b": wave_b,
            "wave_c": wave_c,
        }


class WaterDeformationLayer:
    name = "deformation"

    def apply(self, frame: EffectFrame, context: EffectContext) -> None:
        data = frame.data["water"]
        assets = context.assets
        config = data["config"]
        x, y = data["x"], data["y"]
        flow_x, flow_y = data["flow_x"], data["flow_y"]
        flow_speed, mobility = data["flow_speed"], data["mobility"]
        wave_a, wave_b, wave_c = data["wave_a"], data["wave_b"], data["wave_c"]

        depth_scale = 0.65 + assets.depth * 0.7
        amplitude = (
            np.float32(config.strength)
            * depth_scale
            * data["style_scale"]
            * flow_speed
            * mobility
        )
        displacement_along = amplitude * (0.2 + config.advection * 0.45) * (
            wave_a + wave_c * config.turbulence * 0.35
        )
        displacement_across = amplitude * config.cross_flow * (
            wave_b + wave_c * config.turbulence * 0.28
        )
        dx = flow_x * displacement_along - flow_y * displacement_across
        dy = flow_y * displacement_along + flow_x * displacement_across

        warped = _bilinear_remap(frame.original, x + dx, y + dy)
        if config.shimmer > 0:
            shimmer = (
                wave_a
                * wave_b
                * np.float32(config.shimmer * 10.0)
                * (0.6 + assets.style.contrast * 0.4)
            )
            warped = np.clip(warped + shimmer[..., None], 0.0, 255.0)

        alpha = np.clip(
            assets.mask * config.opacity * mobility,
            0.0,
            1.0,
        )[..., None]
        frame.current = warped * alpha + frame.original * (1.0 - alpha)


class WaterHighlightLayer:
    name = "highlights"

    def apply(self, frame: EffectFrame, context: EffectContext) -> None:
        data = frame.data["water"]
        assets = context.assets
        config = data["config"]
        wave_a, wave_b, wave_c = data["wave_a"], data["wave_b"], data["wave_c"]
        flow_speed, mobility = data["flow_speed"], data["mobility"]

        highlight_color = _water_highlight_color(assets)
        crest = np.clip(
            wave_a * 0.48 + wave_b * 0.28 + wave_c * 0.24,
            0.0,
            1.0,
        )
        highlight_alpha = (
            crest**2
            * config.highlight
            * flow_speed
            * mobility
            * assets.mask
        )[..., None]
        frame.current = (
            frame.current * (1.0 - highlight_alpha)
            + highlight_color * highlight_alpha
        )


class WaterFoamLayer:
    name = "foam"

    def apply(self, frame: EffectFrame, context: EffectContext) -> None:
        data = frame.data["water"]
        assets = context.assets
        config = data["config"]
        highlight_color = _water_highlight_color(assets)

        foam_pulse = 0.7 + 0.3 * np.sin(
            data["phase"] * 2.0
            + data["along"]
            * (np.pi * 2.0 / max(10.0, config.secondary_wavelength))
            + data["phase_c"]
        )
        foam_alpha = np.clip(
            assets.foam * foam_pulse * config.foam_amount * assets.mask,
            0.0,
            0.9,
        )[..., None]
        foam_color = highlight_color * 0.35 + 255.0 * 0.65
        # Foam is composited after motion protection so banks/rocks stay still
        # while the contact foam remains visible beside them.
        frame.current = (
            frame.current * (1.0 - foam_alpha) + foam_color * foam_alpha
        )


class WaterFlowEffect(LayeredEffect):
    effect_type = "water"

    def __init__(self) -> None:
        super().__init__(
            (
                WaterWavesLayer(),
                WaterDeformationLayer(),
                WaterHighlightLayer(),
                WaterFoamLayer(),
            )
        )
