from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

import numpy as np
from PIL import Image

from ..cache import ByteBudgetLRU, effect_cache_budget_bytes
from ..color import srgb_color_to_linear
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
    map_x, map_y = np.broadcast_arrays(map_x, map_y)
    has_channels = image.ndim == 3
    output_shape = map_x.shape + ((image.shape[2],) if has_channels else ())
    output = np.empty(output_shape, dtype=np.float32)
    # Tiling keeps the four gathered RGB neighbours from occupying hundreds of
    # megabytes at 4K while preserving exactly the same interpolation.
    for row_start in range(0, map_x.shape[0], 192):
        row_end = min(map_x.shape[0], row_start + 192)
        x = _reflect_coordinates(map_x[row_start:row_end], width)
        y = _reflect_coordinates(map_y[row_start:row_end], height)

        x0 = np.floor(x).astype(np.int32)
        y0 = np.floor(y).astype(np.int32)
        x1 = np.minimum(x0 + 1, width - 1)
        y1 = np.minimum(y0 + 1, height - 1)

        wx = x - x0
        wy = y - y0
        if has_channels:
            wx = wx[..., None]
            wy = wy[..., None]
        top = image[y0, x0] * (1.0 - wx) + image[y0, x1] * wx
        bottom = image[y1, x0] * (1.0 - wx) + image[y1, x1] * wx
        output[row_start:row_end] = top * (1.0 - wy) + bottom * wy
    return output


def _integrated_flow_coordinates(
    flow_x: np.ndarray,
    flow_y: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    """Build continuous approximate streamline coordinates from a dense flow."""
    height, width = flow_x.shape
    center_x = width // 2
    center_y = height // 2

    # Integrate each coordinate along its natural axis, then anchor the scan
    # lines through the image centre.  Unlike x*flow_x + y*flow_y, a local
    # direction change cannot multiply a tiny vector change by a large pixel
    # coordinate and create a phase discontinuity.
    along = np.cumsum(flow_x, axis=1, dtype=np.float32)
    along -= along[:, center_x : center_x + 1]
    row_offsets = np.cumsum(flow_y[:, center_x], dtype=np.float32)
    row_offsets -= row_offsets[center_y]
    along += row_offsets[:, None]

    across = np.cumsum(-flow_y, axis=0, dtype=np.float32)
    across -= across[center_y : center_y + 1, :]
    column_offsets = np.cumsum(flow_x[center_y, :], dtype=np.float32)
    column_offsets -= column_offsets[center_x]
    across += column_offsets[None, :]
    return along, across


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
        return srgb_color_to_linear(
            np.array([205.0, 230.0, 242.0], dtype=np.float32)
        )
    color = max(colors, key=lambda item: float(item @ np.array([0.21, 0.72, 0.07])))
    display_color = color.astype(np.float32) * 0.45 + 255.0 * 0.55
    return srgb_color_to_linear(display_color)


class WaterWavesLayer:
    name = "waves"

    def __init__(self) -> None:
        self._cache: ByteBudgetLRU[
            tuple[int, int, int, int, int], dict[str, object]
        ] = ByteBudgetLRU(effect_cache_budget_bytes())

    def _static_data(self, context: EffectContext) -> dict[str, object]:
        assets = context.assets
        cache_key = (
            assets.cache_token,
            id(assets),
            context.seed,
            assets.width,
            assets.height,
        )

        def create() -> dict[str, object]:
            height, width = assets.mask.shape
            x = np.arange(width, dtype=np.float32)[None, :]
            y = np.arange(height, dtype=np.float32)[:, None]
            along, across = _integrated_flow_coordinates(
                assets.flow[..., 0],
                assets.flow[..., 1],
            )
            rng = context.rng("water-waves")
            phase_a, phase_b, phase_c = rng.uniform(
                0.0, np.pi * 2.0, size=3
            ).astype(np.float32)
            return {
                "x": x,
                "y": y,
                "along": along,
                "across": across,
                "mobility": np.clip(1.0 - assets.obstacles, 0.0, 1.0),
                "depth_scale": 0.65 + assets.depth * 0.7,
                "style_scale": np.float32(
                    np.clip(
                        0.85
                        + assets.style.edge_softness * 0.25
                        - assets.style.grain * 0.1,
                        0.7,
                        1.15,
                    )
                ),
                "phase_a": phase_a,
                "phase_b": phase_b,
                "phase_c": phase_c,
                "frequency_scale": np.float32(rng.uniform(0.9, 1.1)),
                "highlight_color": _water_highlight_color(assets),
                "foam_region": _foam_region(assets.foam, margin=50),
            }

        return self._cache.get_or_create(cache_key, create)

    def apply(self, frame: EffectFrame, context: EffectContext) -> None:
        config = WaterFlowParams.from_mapping(context.params)
        phase = np.float32(context.phase(config.cycles))
        static = self._static_data(context)
        along = static["along"]
        across = static["across"]

        # Temporal multipliers stay integer so t=1 wraps exactly to t=0.
        # Speed changes amplitude; the integrated coordinates keep phase smooth
        # through bends and reversals in the editable flow field.
        local_phase = phase
        wave_a = np.sin(
            along
            * (np.pi * 2.0 / config.wavelength)
            * static["frequency_scale"]
            - local_phase
            + static["phase_a"]
        )
        wave_b = np.sin(
            across
            * (np.pi * 2.0 / config.secondary_wavelength)
            - local_phase * 2.0
            + static["phase_b"]
        )
        wave_c = np.sin(
            (along + across * 0.38)
            * (np.pi * 2.0 / max(8.0, config.wavelength * 0.46))
            - local_phase * 3.0
            + static["phase_c"]
        )

        frame.data["water"] = dict(static)
        frame.data["water"].update({
            "config": config,
            "phase": phase,
            "flow_x": context.flow[..., 0],
            "flow_y": context.flow[..., 1],
            "flow_speed": context.speed,
            "wave_a": wave_a,
            "wave_b": wave_b,
            "wave_c": wave_c,
        })


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

        amplitude = (
            np.float32(config.strength)
            * data["depth_scale"]
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
            warped = np.clip(warped + shimmer[..., None] / 255.0, 0.0, 1.0)

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

        highlight_color = data["highlight_color"]
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
        highlight_color = data["highlight_color"]
        region = data["foam_region"]
        if config.foam_amount <= 0 or region is None:
            return
        y_slice, x_slice = region
        region_height = y_slice.stop - y_slice.start
        region_width = x_slice.stop - x_slice.start
        region_pixels = region_height * region_width
        if region_pixels > 6_000_000:
            sample_step = 4
        elif region_pixels > 1_000_000:
            sample_step = 2
        else:
            sample_step = 1
        sample_y = slice(y_slice.start, y_slice.stop, sample_step)
        sample_x = slice(x_slice.start, x_slice.stop, sample_step)
        flow_x, flow_y = data["flow_x"], data["flow_y"]
        flow_speed, mobility = data["flow_speed"], data["mobility"]
        x, y = data["x"], data["y"]
        region_x = x[:, sample_x]
        region_y = y[sample_y, :]
        region_flow_x = flow_x[sample_y, sample_x]
        region_flow_y = flow_y[sample_y, sample_x]
        region_mobility = mobility[sample_y, sample_x]

        # Two forward-moving samples crossfade over one closed trajectory.
        # At p=0 the first sample is the original foam map; near p=1 the
        # second sample reaches that same map, avoiding a visible loop cut.
        progress = float(np.mod(data["phase"] / (np.pi * 2.0), 1.0))
        blend = progress * progress * (3.0 - 2.0 * progress)
        travel = np.clip(
            config.secondary_wavelength * (0.22 + config.advection * 0.22),
            6.0,
            48.0,
        )
        local_travel = (
            travel
            * (0.35 + flow_speed[sample_y, sample_x] * 0.65)
            * region_mobility
        )

        def advect(offset: float) -> np.ndarray:
            return _bilinear_remap(
                assets.foam,
                region_x - region_flow_x * local_travel * offset,
                region_y - region_flow_y * local_travel * offset,
            )

        advected = advect(progress) * (1.0 - blend) + advect(
            progress - 1.0
        ) * blend
        # Keep some contact foam attached to banks and rocks while a lighter
        # part travels downstream. Fine wave detail prevents a flat mask look.
        region_foam = assets.foam[sample_y, sample_x]
        foam_field = np.maximum(region_foam * 0.32, advected * 0.88)
        foam_detail = np.clip(
            0.72 + data["wave_c"][sample_y, sample_x] * 0.28,
            0.35,
            1.0,
        )
        foam_pulse = 0.78 + 0.22 * np.sin(
            data["phase"] * 2.0
            + data["along"][sample_y, sample_x]
            * (np.pi * 2.0 / max(10.0, config.secondary_wavelength))
            + data["phase_c"]
        )
        foam_alpha = np.clip(
            foam_field
            * foam_detail
            * foam_pulse
            * config.foam_amount
            * assets.mask[sample_y, sample_x],
            0.0,
            0.9,
        )
        if sample_step > 1:
            foam_alpha = np.asarray(
                Image.fromarray(foam_alpha.astype(np.float32), mode="F").resize(
                    (region_width, region_height),
                    Image.Resampling.BILINEAR,
                ),
                dtype=np.float32,
            )
        foam_alpha = foam_alpha[..., None]
        foam_color = highlight_color * 0.35 + 0.65
        # Foam is composited after motion protection so banks/rocks stay still
        # while the contact foam remains visible beside them.
        target = frame.current[y_slice, x_slice]
        frame.current[y_slice, x_slice] = (
            target * (1.0 - foam_alpha) + foam_color * foam_alpha
        )


def _foam_region(
    foam: np.ndarray,
    *,
    margin: int,
) -> tuple[slice, slice] | None:
    selected = foam > 1e-4
    selected_y = np.flatnonzero(np.any(selected, axis=1))
    selected_x = np.flatnonzero(np.any(selected, axis=0))
    if selected_x.size == 0 or selected_y.size == 0:
        return None
    height, width = foam.shape
    x0 = max(0, int(selected_x.min()) - margin)
    x1 = min(width, int(selected_x.max()) + margin + 1)
    y0 = max(0, int(selected_y.min()) - margin)
    y1 = min(height, int(selected_y.max()) + margin + 1)
    return slice(y0, y1), slice(x0, x1)


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
