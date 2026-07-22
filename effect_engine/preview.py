from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping

import numpy as np
from PIL import Image

from .models import EffectAssets
from .parameters import renderer_params_from_card
from .preset_registry import resolve_card_preset
from .preparation import create_preparation_pipeline
from .project import find_shape_card, load_project, prepare_project_shape, resolve_background_path
from .renderer import DeterministicEffectEngine
from .storage import EffectAssetStore


@dataclass(slots=True)
class PreviewResult:
    frames: list[Image.Image]
    assets_dir: Path
    effect_type: str
    shape_id: int
    fps: int
    params: dict[str, float]
    preset_id: str | None = None
    debug_maps: dict[str, Image.Image] = field(default_factory=dict)
    warnings: tuple[str, ...] = ()


def effect_asset_debug_maps(assets: EffectAssets) -> dict[str, Image.Image]:
    flow = np.asarray(assets.flow, dtype=np.float32)
    selection = np.asarray(assets.mask, dtype=np.float32)
    flow_rgb = np.stack(
        (
            np.clip(flow[..., 0] * 0.5 + 0.5, 0.0, 1.0),
            np.clip(flow[..., 1] * 0.5 + 0.5, 0.0, 1.0),
            np.asarray(assets.speed, dtype=np.float32),
        ),
        axis=-1,
    ) * selection[..., None]
    speed = np.asarray(assets.speed, dtype=np.float32)
    speed_rgb = np.stack(
        (speed, np.sqrt(speed) * 0.75, 1.0 - speed), axis=-1
    ) * selection[..., None]
    obstacle = np.asarray(assets.obstacles, dtype=np.float32)
    obstacle_rgb = np.stack(
        (obstacle, obstacle * 0.12, obstacle * 0.08), axis=-1
    )
    foam = np.asarray(assets.foam, dtype=np.float32)

    def gray(value: np.ndarray) -> Image.Image:
        return Image.fromarray(
            np.rint(np.clip(value, 0.0, 1.0) * 255.0).astype(np.uint8),
            mode="L",
        ).convert("RGB")

    def rgb(value: np.ndarray) -> Image.Image:
        return Image.fromarray(
            np.rint(np.clip(value, 0.0, 1.0) * 255.0).astype(np.uint8),
            mode="RGB",
        )

    return {
        "Mask": gray(assets.mask),
        "Depth": gray(assets.depth),
        "Flow": rgb(flow_rgb),
        "Speed": rgb(speed_rgb),
        "Obstacles": rgb(obstacle_rgb),
        "Foam": gray(foam),
    }


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
    dense_maps = {
        name: np.asarray(
            Image.fromarray(getattr(assets, name), mode="F").resize(
                (width, height), Image.Resampling.BILINEAR
            ),
            dtype=np.float32,
        )
        for name in ("speed", "obstacles", "foam")
    }
    metadata = dict(assets.metadata)
    metadata["preview_source_size"] = {"width": assets.width, "height": assets.height}
    return EffectAssets(
        effect_type=assets.effect_type,
        seed=assets.seed,
        mask=np.asarray(mask_image, dtype=np.float32),
        depth=np.asarray(depth_image, dtype=np.float32),
        flow=np.stack(flow_channels, axis=-1),
        speed=dense_maps["speed"],
        obstacles=dense_maps["obstacles"],
        foam=dense_maps["foam"],
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
    use_ai_preparation: bool | None = None,
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
    preset = resolve_card_preset(card, effect_type)

    assets, assets_dir = prepare_project_shape(
        path,
        shape_id,
        effect_type=effect_type,
        preset_id=preset.preset_id if preset is not None else None,
        card_override=card,
        seed=seed,
        direction=direction_override,
        pipeline=create_preparation_pipeline(use_ai_preparation),
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
    if preview_size != source_size:
        scale = min(
            preview_size[0] / source_size[0],
            preview_size[1] / source_size[1],
        )
        for name in (
            "strength",
            "wavelength",
            "secondary_wavelength",
            "drop_length",
        ):
            if name in params:
                params[name] = float(params[name]) * scale
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
        debug_maps=effect_asset_debug_maps(preview_assets),
        warnings=tuple(
            f"{stage}: {message}"
            for stage, message in (
                assets.metadata.get("provider_warnings") or {}
            ).items()
        ),
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
    use_ai_preparation: bool | None = None,
    prepared_assets_dir: str | Path | None = None,
) -> Path:
    """Render a full-resolution deterministic loop directly to an H.264 file."""
    path, project = load_project(project_path)
    card = (
        dict(card_override)
        if card_override is not None
        else find_shape_card(project, int(shape_id))
    )
    effect_type = str(card.get("tool_type") or "water").strip().lower()
    preset = resolve_card_preset(card, effect_type)
    if prepared_assets_dir is not None:
        assets = EffectAssetStore.load(prepared_assets_dir)
        if assets.effect_type != effect_type:
            raise ValueError("Prepared assets do not match the selected effect")
    else:
        assets, _ = prepare_project_shape(
            path,
            shape_id,
            effect_type=effect_type,
            preset_id=preset.preset_id if preset is not None else None,
            card_override=card,
            seed=seed,
            direction=direction_override,
            pipeline=create_preparation_pipeline(use_ai_preparation),
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
