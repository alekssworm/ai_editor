from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from ..cache import ByteBudgetLRU, effect_cache_budget_bytes
from ..color import srgb_color_to_linear
from ..context import EffectContext
from ..layers import EffectFrame, LayeredEffect
from ..spatial import (
    bilinear_remap,
    gaussian_blur_float,
    integrated_flow_coordinates,
    periodic_sine,
)


@dataclass(frozen=True, slots=True)
class FireParams:
    intensity: float = 0.72
    flame_height: float = 0.72
    turbulence: float = 0.48
    heat_distortion: float = 2.2
    glow: float = 0.34
    ember_density: float = 0.25
    opacity: float = 0.88
    cycles: int = 1

    @classmethod
    def from_mapping(cls, values: Mapping[str, float] | None) -> "FireParams":
        values = values or {}
        defaults = cls()
        return cls(
            intensity=float(
                np.clip(values.get("intensity", defaults.intensity), 0.0, 1.5)
            ),
            flame_height=float(
                np.clip(values.get("flame_height", defaults.flame_height), 0.15, 1.0)
            ),
            turbulence=float(
                np.clip(values.get("turbulence", defaults.turbulence), 0.0, 1.0)
            ),
            heat_distortion=float(
                np.clip(
                    values.get("heat_distortion", defaults.heat_distortion),
                    0.0,
                    8.0,
                )
            ),
            glow=float(np.clip(values.get("glow", defaults.glow), 0.0, 1.0)),
            ember_density=float(
                np.clip(
                    values.get("ember_density", defaults.ember_density),
                    0.0,
                    1.0,
                )
            ),
            opacity=float(np.clip(values.get("opacity", defaults.opacity), 0.0, 1.0)),
            cycles=max(1, min(6, int(values.get("cycles", defaults.cycles)))),
        )


def _fire_colors(context: EffectContext) -> tuple[np.ndarray, ...]:
    warm = (
        np.array([255.0, 247.0, 195.0], dtype=np.float32),
        np.array([255.0, 171.0, 48.0], dtype=np.float32),
        np.array([226.0, 56.0, 10.0], dtype=np.float32),
    )
    palette: list[np.ndarray] = []
    for value in context.assets.style.palette:
        text = str(value).lstrip("#")
        if len(text) != 6:
            continue
        try:
            palette.append(
                np.array(
                    [int(text[index : index + 2], 16) for index in (0, 2, 4)],
                    dtype=np.float32,
                )
            )
        except ValueError:
            continue
    if palette:
        lightest = max(palette, key=lambda color: float(color.mean()))
        warm = (
            warm[0] * 0.82 + lightest * 0.18,
            warm[1] * 0.9 + lightest * 0.1,
            warm[2],
        )
    return tuple(srgb_color_to_linear(color) for color in warm)


class FireFieldLayer:
    name = "field"

    def __init__(self) -> None:
        self._cache: ByteBudgetLRU[
            tuple[int, int, int, int, int], dict[str, object]
        ] = ByteBudgetLRU(min(effect_cache_budget_bytes(), 64 * 1024 * 1024))

    def _static_data(self, context: EffectContext) -> dict[str, object]:
        height, width = context.mask.shape
        key = (
            context.assets.cache_token,
            id(context.assets),
            context.seed,
            width,
            height,
        )

        def create() -> dict[str, object]:
            y, x = np.mgrid[0:height, 0:width].astype(np.float32)
            selected_y = np.flatnonzero(np.any(context.mask > 0.05, axis=1))
            if selected_y.size:
                top, bottom = float(selected_y.min()), float(selected_y.max())
            else:
                top, bottom = 0.0, float(max(1, height - 1))
            vertical = np.clip((y - top) / max(1.0, bottom - top), 0.0, 1.0)
            along, across = integrated_flow_coordinates(
                context.flow[..., 0],
                context.flow[..., 1],
            )
            phases = context.rng("fire-field").uniform(
                0.0,
                np.pi * 2.0,
                size=4,
            ).astype(np.float32)
            return {
                "x": x,
                "y": y,
                "vertical": vertical,
                "along": along,
                "across": across,
                "phases": phases,
                "colors": _fire_colors(context),
            }

        return self._cache.get_or_create(key, create)

    def apply(self, frame: EffectFrame, context: EffectContext) -> None:
        config = FireParams.from_mapping(context.params)
        data = self._static_data(context)
        phase = np.float32(context.phase(config.cycles))
        x = data["x"]
        y = data["y"]
        along = data["along"]
        across = data["across"]
        phases = data["phases"]
        height, width = context.mask.shape
        noise = (
            periodic_sine(
                x / max(5.0, width * 0.055)
                + along / max(9.0, height * 0.12),
                phase,
                temporal_cycles=2,
                offset=phases[0],
            )
            * 0.34
            + periodic_sine(
                y / max(7.0, height * 0.09)
                - across / max(8.0, width * 0.11),
                phase,
                temporal_cycles=3,
                offset=phases[1],
            )
            * 0.27
            + periodic_sine(
                (x * 0.73 + y * 0.31)
                / max(4.0, min(width, height) * 0.045),
                phase,
                temporal_cycles=5,
                offset=phases[2],
            )
            * (0.11 + config.turbulence * 0.14)
            + periodic_sine(
                (x * 1.4 - y * 0.82)
                / max(3.0, min(width, height) * 0.028),
                phase,
                temporal_cycles=7,
                offset=phases[3],
            )
            * config.turbulence
            * 0.08
        )
        bottomness = data["vertical"]
        height_envelope = np.clip(
            1.0 - (1.0 - bottomness) * (1.15 - config.flame_height * 0.72),
            0.0,
            1.0,
        )
        threshold = 0.05 + (1.0 - height_envelope) * 0.48
        flame = np.clip((noise - threshold + 0.34) * 1.75, 0.0, 1.0)
        flame *= np.clip(context.mask * (1.0 - context.obstacles), 0.0, 1.0)
        core = np.clip((flame - 0.46) * 1.85, 0.0, 1.0)
        frame.data["fire"] = dict(data)
        frame.data["fire"].update(
            {
                "config": config,
                "phase": phase,
                "flame": flame.astype(np.float32),
                "core": core.astype(np.float32),
                "noise": noise.astype(np.float32),
            }
        )


class FireDistortionLayer:
    name = "distortion"

    def apply(self, frame: EffectFrame, context: EffectContext) -> None:
        data = frame.data["fire"]
        config: FireParams = data["config"]
        if config.heat_distortion <= 0.0:
            return
        noise = data["noise"]
        gradient_y = (
            np.gradient(noise, axis=0)
            if noise.shape[0] > 1
            else np.zeros_like(noise)
        )
        gradient_x = (
            np.gradient(noise, axis=1)
            if noise.shape[1] > 1
            else np.zeros_like(noise)
        )
        influence = (
            data["flame"]
            * context.mask
            * (0.35 + context.depth * 0.65)
            * config.heat_distortion
        )
        map_x = data["x"] + gradient_y * influence
        map_y = data["y"] - gradient_x * influence * 0.45
        distorted = bilinear_remap(frame.original, map_x, map_y)
        alpha = np.clip(influence / 8.0, 0.0, 0.5)[..., None]
        frame.current = frame.current * (1.0 - alpha) + distorted * alpha


class FireFlameLayer:
    name = "flames"

    def apply(self, frame: EffectFrame, context: EffectContext) -> None:
        data = frame.data["fire"]
        config: FireParams = data["config"]
        light, orange, red = data["colors"]
        flame = data["flame"]
        core = data["core"]
        color = (
            red
            + (orange - red) * np.clip(flame * 1.35, 0.0, 1.0)[..., None]
            + (light - orange) * core[..., None]
        )
        alpha = np.clip(
            flame
            * context.mask
            * config.opacity
            * config.intensity
            * (0.55 + context.depth * 0.45),
            0.0,
            0.96,
        )[..., None]
        frame.current = frame.current * (1.0 - alpha) + color * alpha


class FireGlowLayer:
    name = "glow"

    def apply(self, frame: EffectFrame, context: EffectContext) -> None:
        data = frame.data["fire"]
        config: FireParams = data["config"]
        if config.glow <= 0.0:
            return
        height, width = context.mask.shape
        radius = max(1.0, min(width, height) * 0.018)
        glow = np.clip(
            gaussian_blur_float(data["flame"], radius),
            0.0,
            1.0,
        )
        glow_alpha = np.clip(
            glow
            * context.mask
            * np.clip(1.0 - context.obstacles * 0.72, 0.0, 1.0)
            * config.glow
            * config.intensity
            * 0.42,
            0.0,
            0.42,
        )[..., None]
        glow_color = data["colors"][1] * 0.68 + data["colors"][0] * 0.32
        frame.current = frame.current * (1.0 - glow_alpha) + glow_color * glow_alpha


class FireEmberLayer:
    name = "embers"

    def __init__(self) -> None:
        self._cache: ByteBudgetLRU[
            tuple[int, int, int, int, int, float], dict[str, np.ndarray]
        ] = ByteBudgetLRU(min(effect_cache_budget_bytes(), 8 * 1024 * 1024))

    def _particles(
        self,
        context: EffectContext,
        density: float,
    ) -> dict[str, np.ndarray]:
        height, width = context.mask.shape
        key = (
            context.assets.cache_token,
            id(context.assets),
            context.seed,
            width,
            height,
            round(density, 5),
        )

        def create() -> dict[str, np.ndarray]:
            count = max(4, min(900, int(width * height * density / 2400.0)))
            rng = context.rng("fire-embers")
            return {
                "x": rng.uniform(0.0, width, size=count),
                "y": rng.uniform(0.0, height, size=count),
                "phase": rng.uniform(0.0, 1.0, size=count),
                "sway": rng.uniform(5.0, max(6.0, width * 0.06), size=count),
                "brightness": rng.uniform(0.45, 1.0, size=count),
            }

        return self._cache.get_or_create(key, create)

    def apply(self, frame: EffectFrame, context: EffectContext) -> None:
        data = frame.data["fire"]
        config: FireParams = data["config"]
        if config.ember_density <= 0.0:
            return
        height, width = context.mask.shape
        particles = self._particles(context, config.ember_density)
        trajectory = particles["phase"] + context.time * config.cycles
        progress = np.mod(trajectory, 1.0)
        y = np.mod(particles["y"] - progress * height * 0.42, height)
        x = np.mod(
            particles["x"]
            + np.sin(np.pi * 2.0 * trajectory) * particles["sway"],
            width,
        )
        embers = Image.new("L", (width, height), 0)
        painter = ImageDraw.Draw(embers)
        for index in range(len(x)):
            px = int(np.clip(round(x[index]), 0, width - 1))
            py = int(np.clip(round(y[index]), 0, height - 1))
            if (
                context.mask[py, px] <= 0.05
                or context.obstacles[py, px] >= 0.75
            ):
                continue
            value = int(round(255.0 * particles["brightness"][index]))
            painter.ellipse((px - 1, py - 1, px + 1, py + 1), fill=value)
        alpha = np.asarray(
            embers.filter(ImageFilter.GaussianBlur(radius=0.45)),
            dtype=np.float32,
        ) / 255.0
        alpha = np.clip(
            alpha
            * context.mask
            * np.clip(1.0 - context.obstacles, 0.0, 1.0)
            * config.ember_density
            * config.intensity
            * 0.7,
            0.0,
            0.8,
        )[..., None]
        frame.current = frame.current * (1.0 - alpha) + data["colors"][0] * alpha


class FireEffect(LayeredEffect):
    effect_type = "fire"

    def __init__(self) -> None:
        super().__init__(
            (
                FireFieldLayer(),
                FireDistortionLayer(),
                FireFlameLayer(),
                FireGlowLayer(),
                FireEmberLayer(),
            )
        )
