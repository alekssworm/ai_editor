from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

import numpy as np
from PIL import Image

from .models import EffectAssets
from .parameters import renderer_params_from_card
from .preset_registry import resolve_card_preset
from .project import find_shape_card, load_project, prepare_project_shape, resolve_background_path
from .renderer import DeterministicEffectEngine


@dataclass(slots=True)
class PreviewResult:
    frames: list[Image.Image]
    assets_dir: Path
    effect_type: str
    shape_id: int
    fps: int
    params: dict[str, float]
    preset_id: str | None = None


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
    preset = resolve_card_preset(card, effect_type)

    assets, assets_dir = prepare_project_shape(
        path,
        shape_id,
        effect_type=effect_type,
        preset_id=preset.preset_id if preset is not None else None,
        card_override=card,
        seed=seed,
        direction=direction_override,
    )
    background_path = resolve_background_path(path, project)
    with Image.open(background_path) as source:
        image = source.convert("RGB")

    source_size = image.size
    preview_size = fit_size(image.size, max_dimension)
    if preview_size != image.size:
        image = image.resize(preview_size, Image.Resampling.LANCZOS)
    preview_assets = resize_effect_assets(assets, preview_size)
    params = renderer_params_from_card(card)
    if preview_size != source_size and "strength" in params:
        scale = min(
            preview_size[0] / source_size[0],
            preview_size[1] / source_size[1],
        )
        params["strength"] = float(params["strength"]) * scale
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
        preset_id=preset.preset_id if preset is not None else None,
    )


def export_project_loop(
    project_path: str | Path,
    shape_id: int,
    output_path: str | Path,
    *,
    card_override: Mapping[str, Any] | None = None,
    direction_override: tuple[float, float] | None = None,
    frame_count: int = 72,
    fps: int = 24,
    crf: int = 18,
    seed: int = 1,
) -> Path:
    """Render a full-resolution deterministic loop directly to an H.264 file."""
    path, project = load_project(project_path)
    card = (
        dict(card_override)
        if card_override is not None
        else find_shape_card(project, int(shape_id))
    )
    effect_type = str(card.get("tool_type") or "water").strip().lower()
    if effect_type != "water":
        raise ValueError("Deterministic export currently supports only the water tool")
    preset = resolve_card_preset(card, effect_type)
    assets, _ = prepare_project_shape(
        path,
        shape_id,
        effect_type=effect_type,
        preset_id=preset.preset_id if preset is not None else None,
        card_override=card,
        seed=seed,
        direction=direction_override,
    )
    background_path = resolve_background_path(path, project)
    with Image.open(background_path) as source:
        image = source.convert("RGB")
    params = renderer_params_from_card(card)
    return DeterministicEffectEngine().export_mp4(
        image,
        assets,
        output_path,
        frame_count=frame_count,
        fps=fps,
        crf=crf,
        params=params,
    )
