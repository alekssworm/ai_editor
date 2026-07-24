from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from ..cache import ByteBudgetLRU, effect_cache_budget_bytes
from ..color import srgb_color_to_linear
from ..context import EffectContext
from ..layers import EffectFrame, LayeredEffect


@dataclass(frozen=True, slots=True)
class RainParams:
    density: float = 0.55
    drop_length: float = 18.0
    opacity: float = 0.52
    cycles: int = 2
    wind: float = 0.12
    mist: float = 0.08
    brightness: float = 0.8
    strength: float = 4.0

    @classmethod
    def from_mapping(cls, values: Mapping[str, float] | None) -> "RainParams":
        values = values or {}
        defaults = cls()
        return cls(
            density=float(np.clip(values.get("density", defaults.density), 0.02, 1.0)),
            drop_length=float(
                np.clip(values.get("drop_length", defaults.drop_length), 3.0, 80.0)
            ),
            opacity=float(np.clip(values.get("opacity", defaults.opacity), 0.0, 1.0)),
            cycles=max(1, min(8, int(values.get("cycles", defaults.cycles)))),
            wind=float(np.clip(values.get("wind", defaults.wind), -1.0, 1.0)),
            mist=float(np.clip(values.get("mist", defaults.mist), 0.0, 0.6)),
            brightness=float(
                np.clip(values.get("brightness", defaults.brightness), 0.1, 1.0)
            ),
            strength=float(
                np.clip(values.get("strength", defaults.strength), 0.25, 32.0)
            ),
        )


def _rain_direction(context: EffectContext, wind: float) -> tuple[float, float]:
    raw = context.assets.metadata.get("direction")
    try:
        dx, dy = float(raw[0]), float(raw[1])
    except (TypeError, ValueError, IndexError):
        selected = context.mask > 0.1
        if np.any(selected):
            dx = float(context.flow[..., 0][selected].mean())
            dy = float(context.flow[..., 1][selected].mean())
        else:
            dx, dy = 0.12, 1.0
    # Rain defaults downwards when preparation had no explicit motion guide.
    if raw is None:
        dx, dy = 0.12, 1.0
    dx += float(wind)
    length = max(1e-6, float(np.hypot(dx, dy)))
    return dx / length, dy / length


def _rain_color(context: EffectContext) -> np.ndarray:
    palette = []
    for value in context.assets.style.palette:
        text = str(value).lstrip("#")
        if len(text) != 6:
            continue
        try:
            palette.append(
                np.array([int(text[index : index + 2], 16) for index in (0, 2, 4)])
            )
        except ValueError:
            continue
    base = (
        max(palette, key=lambda color: float(color.mean())).astype(np.float32)
        if palette
        else np.array([185.0, 210.0, 230.0], dtype=np.float32)
    )
    display_color = np.clip(
        base * 0.38 + np.array([205.0, 225.0, 255.0]) * 0.62,
        0,
        255,
    )
    return srgb_color_to_linear(display_color)


class RainStreakLayer:
    name = "streaks"

    def __init__(self) -> None:
        self._particle_cache: ByteBudgetLRU[
            tuple[int, int, int, int, int, float], dict[str, np.ndarray]
        ] = ByteBudgetLRU(min(effect_cache_budget_bytes(), 32 * 1024 * 1024))

    def _particle_data(
        self,
        context: EffectContext,
        density: float,
    ) -> dict[str, np.ndarray]:
        height, width = context.mask.shape
        cache_key = (
            context.assets.cache_token,
            id(context.assets),
            context.seed,
            width,
            height,
            round(float(density), 6),
        )

        def create() -> dict[str, np.ndarray]:
            rng = context.rng("rain-streaks")
            area = width * height
            count = max(12, min(4000, int(area * density / 700.0)))
            return {
                "base_x": rng.uniform(0.0, width, size=count),
                "base_y": rng.uniform(0.0, height, size=count),
                "phase": rng.uniform(0.0, 1.0, size=count),
                "length_scale": rng.uniform(0.55, 1.35, size=count),
                "intensity": rng.uniform(0.35, 1.0, size=count),
                "thickness": rng.choice((1, 1, 1, 2), size=count),
            }

        return self._particle_cache.get_or_create(cache_key, create)

    def apply(self, frame: EffectFrame, context: EffectContext) -> None:
        config = RainParams.from_mapping(context.params)
        height, width = context.mask.shape
        particles = self._particle_data(context, config.density)
        base_x = particles["base_x"]
        base_y = particles["base_y"]
        particle_phase = particles["phase"]
        count = len(base_x)

        direction_x, direction_y = _rain_direction(context, config.wind)
        trajectory = particle_phase + context.time * config.cycles
        progress = np.mod(trajectory, 1.0)
        initial_sine = np.sin(np.pi * 2.0 * particle_phase)
        current_sine = np.sin(np.pi * 2.0 * trajectory)
        if abs(direction_y) >= abs(direction_x):
            head_y = np.mod(
                base_y + np.sign(direction_y or 1.0) * progress * height,
                height,
            )
            slope = direction_x / max(abs(direction_y), 1e-6)
            sway = min(width * 0.25, abs(slope) * height / (np.pi * 2.0))
            head_x = np.mod(
                base_x + np.sign(direction_x) * sway * (current_sine - initial_sine),
                width,
            )
        else:
            head_x = np.mod(
                base_x + np.sign(direction_x or 1.0) * progress * width,
                width,
            )
            slope = direction_y / max(abs(direction_x), 1e-6)
            sway = min(height * 0.25, abs(slope) * width / (np.pi * 2.0))
            head_y = np.mod(
                base_y + np.sign(direction_y) * sway * (current_sine - initial_sine),
                height,
            )
        strength_scale = np.clip(0.72 + config.strength / 14.0, 0.75, 2.0)

        streaks = Image.new("L", (width, height), 0)
        painter = ImageDraw.Draw(streaks)
        for index in range(count):
            drop_length = (
                config.drop_length
                * particles["length_scale"][index]
                * strength_scale
            )
            end_x = head_x[index] - direction_x * drop_length
            end_y = head_y[index] - direction_y * drop_length
            alpha = round(255.0 * particles["intensity"][index])
            line = (
                float(head_x[index]),
                float(head_y[index]),
                float(end_x),
                float(end_y),
            )
            x_offsets = [0]
            y_offsets = [0]
            if min(line[0], line[2]) < 0:
                x_offsets.append(width)
            if max(line[0], line[2]) >= width:
                x_offsets.append(-width)
            if min(line[1], line[3]) < 0:
                y_offsets.append(height)
            if max(line[1], line[3]) >= height:
                y_offsets.append(-height)
            for offset_y in y_offsets:
                for offset_x in x_offsets:
                    painter.line(
                        (
                            line[0] + offset_x,
                            line[1] + offset_y,
                            line[2] + offset_x,
                            line[3] + offset_y,
                        ),
                        fill=alpha,
                        width=int(particles["thickness"][index]),
                    )

        streaks = streaks.filter(ImageFilter.GaussianBlur(radius=0.35))
        alpha = np.asarray(streaks, dtype=np.float32) / 255.0
        alpha *= context.mask * config.opacity
        alpha *= 0.7 + context.depth * 0.3
        alpha = np.clip(alpha, 0.0, 0.92)[..., None]
        color = _rain_color(context) * config.brightness
        frame.current = frame.current * (1.0 - alpha) + color * alpha
        frame.data["rain"] = {"config": config, "color": color}


class RainMistLayer:
    name = "mist"

    def __init__(self) -> None:
        self._cache: ByteBudgetLRU[
            tuple[int, int, int, int, int], dict[str, object]
        ] = ByteBudgetLRU(min(effect_cache_budget_bytes(), 8 * 1024 * 1024))

    def _static_data(self, context: EffectContext) -> dict[str, object]:
        height, width = context.mask.shape
        cache_key = (
            context.assets.cache_token,
            id(context.assets),
            context.seed,
            width,
            height,
        )

        def create() -> dict[str, object]:
            phase_a, phase_b = context.rng("rain-mist").uniform(
                0.0, np.pi * 2.0, size=2
            )
            return {
                "x": np.arange(width, dtype=np.float32)[None, :],
                "y": np.arange(height, dtype=np.float32)[:, None],
                "phase_a": phase_a,
                "phase_b": phase_b,
            }

        return self._cache.get_or_create(cache_key, create)

    def apply(self, frame: EffectFrame, context: EffectContext) -> None:
        data = frame.data["rain"]
        config: RainParams = data["config"]
        if config.mist <= 0:
            return
        height, width = context.mask.shape
        static = self._static_data(context)
        x, y = static["x"], static["y"]
        wave = (
            np.sin(
                x / max(28.0, width * 0.12)
                + context.phase(1)
                + static["phase_a"]
            )
            + np.sin(
                y / max(24.0, height * 0.16)
                - context.phase(2)
                + static["phase_b"]
            )
        ) * 0.25 + 0.5
        alpha = np.clip(
            wave * context.mask * config.mist * (0.55 + context.depth * 0.45),
            0.0,
            0.35,
        )[..., None]
        mist_color = data["color"] * 0.72 + 0.28
        frame.current = frame.current * (1.0 - alpha) + mist_color * alpha


class RainEffect(LayeredEffect):
    effect_type = "rain"

    def __init__(self) -> None:
        super().__init__((RainStreakLayer(), RainMistLayer()))
