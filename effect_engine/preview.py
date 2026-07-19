from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

import numpy as np
from PIL import Image

from .models import EffectAssets
from .project import find_shape_card, load_project, prepare_project_shape, resolve_background_path
from .renderer import DeterministicEffectEngine


_LEVELS = {
    "default": 1.0,
    "low": 0.65,
    "weak": 0.65,
    "normal": 1.0,
    "medium": 1.0,
    "high": 1.45,
    "strong": 1.45,
}

_OPACITY_LEVELS = {
    "default": 0.75,
    "low": 0.45,
    "weak": 0.45,
    "normal": 0.75,
    "medium": 0.75,
    "high": 1.0,
    "strong": 1.0,
}

_WATER_VARIANTS: dict[str, dict[str, float]] = {
    "main_waterfall": {"strength": 6.0, "wavelength": 38.0, "secondary_wavelength": 24.0},
    "main_river": {"strength": 4.5, "wavelength": 64.0, "secondary_wavelength": 34.0},
    "main_still_water": {"strength": 2.0, "wavelength": 92.0, "secondary_wavelength": 58.0},
}


@dataclass(slots=True)
class PreviewResult:
    frames: list[Image.Image]
    assets_dir: Path
    effect_type: str
    shape_id: int
    fps: int
    params: dict[str, float]


def _main_effect(card: Mapping[str, Any] | None) -> tuple[str, dict[str, Any]]:
    main = (card or {}).get("main") or {}
    if not isinstance(main, Mapping):
        return "", {}
    key = str(main.get("key") or "").strip().lower()
    params = main.get("params") or {}
    return key, dict(params) if isinstance(params, Mapping) else {}


def _level(value: Any, values: Mapping[str, float], default: float) -> float:
    return float(values.get(str(value or "default").strip().lower(), default))


def renderer_params_from_card(card: Mapping[str, Any] | None) -> dict[str, float]:
    """Translate the editor's qualitative water settings into renderer values."""
    variant, values = _main_effect(card)
    result = dict(_WATER_VARIANTS.get(variant, _WATER_VARIANTS["main_river"]))

    intensity = _level(values.get("intensity"), _LEVELS, 1.0)
    power = _level(values.get("power"), _LEVELS, 1.0)
    result["strength"] *= intensity * power
    result["opacity"] = _level(values.get("opacity"), _OPACITY_LEVELS, 0.75)

    randomness = _level(values.get("randomness"), _LEVELS, 1.0)
    result["secondary_wavelength"] /= max(0.5, randomness)

    viscosity = _level(values.get("viscosity"), _LEVELS, 1.0)
    result["wavelength"] *= viscosity
    return result


def fit_size(size: tuple[int, int], max_dimension: int) -> tuple[int, int]:
    if max_dimension <= 0:
        raise ValueError("max_dimension must be positive")
    width, height = size
    scale = min(1.0, float(max_dimension) / max(width, height))
    return max(1, round(width * scale)), max(1, round(height * scale))


def resize_effect_assets(assets: EffectAssets, size: tuple[int, int]) -> EffectAssets:
    """Resize dense maps for an interactive preview without altering saved assets."""
    width, height = (int(size[0]), int(size[1]))
    if width <= 0 or height <= 0:
        raise ValueError("preview size must be positive")
    if (width, height) == assets.size:
        return assets

    mask_image = Image.fromarray(assets.mask, mode="F").resize(
        (width, height), Image.Resampling.BILINEAR
    )
    depth_image = Image.fromarray(assets.depth, mode="F").resize(
        (width, height), Image.Resampling.BILINEAR
    )
    flow_channels = [
        np.asarray(
            Image.fromarray(assets.flow[..., channel], mode="F").resize(
                (width, height), Image.Resampling.BILINEAR
            ),
            dtype=np.float32,
        )
        for channel in range(2)
    ]
    metadata = dict(assets.metadata)
    metadata["preview_source_size"] = {"width": assets.width, "height": assets.height}
    return EffectAssets(
        effect_type=assets.effect_type,
        seed=assets.seed,
        mask=np.asarray(mask_image, dtype=np.float32),
        depth=np.asarray(depth_image, dtype=np.float32),
        flow=np.stack(flow_channels, axis=-1),
        style=assets.style,
        textures=dict(assets.textures),
        metadata=metadata,
        version=assets.version,
    )


def build_project_preview(
    project_path: str | Path,
    shape_id: int,
    *,
    card_override: Mapping[str, Any] | None = None,
    direction_override: tuple[float, float] | None = None,
    frame_count: int = 18,
    fps: int = 12,
    max_dimension: int = 640,
    seed: int = 1,
) -> PreviewResult:
    """Prepare full-size assets, then render a lightweight deterministic preview."""
    if fps <= 0:
        raise ValueError("fps must be positive")

    path, project = load_project(project_path)
    card = (
        dict(card_override)
        if card_override is not None
        else find_shape_card(project, int(shape_id))
    )
    effect_type = str(card.get("tool_type") or "water").strip().lower()
    if effect_type != "water":
        raise ValueError("Deterministic preview currently supports only the water tool")

    assets, assets_dir = prepare_project_shape(
        path,
        shape_id,
        effect_type=effect_type,
        seed=seed,
        direction=direction_override,
    )
    background_path = resolve_background_path(path, project)
    with Image.open(background_path) as source:
        image = source.convert("RGB")

    preview_size = fit_size(image.size, max_dimension)
    if preview_size != image.size:
        image = image.resize(preview_size, Image.Resampling.LANCZOS)
    preview_assets = resize_effect_assets(assets, preview_size)
    params = renderer_params_from_card(card)
    frames = DeterministicEffectEngine().render_frames(
        image,
        preview_assets,
        frame_count=frame_count,
        params=params,
    )
    return PreviewResult(
        frames=frames,
        assets_dir=assets_dir,
        effect_type=effect_type,
        shape_id=int(shape_id),
        fps=int(fps),
        params=params,
    )
