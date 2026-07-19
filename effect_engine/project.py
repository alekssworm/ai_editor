from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw

from .models import EffectAssets
from .preparation import PreparationPipeline
from .storage import EffectAssetStore


def load_project(project_path: str | Path) -> tuple[Path, dict[str, Any]]:
    path = Path(project_path).resolve()
    return path, json.loads(path.read_text(encoding="utf-8"))


def resolve_background_path(project_path: Path, project: dict[str, Any]) -> Path:
    raw_path = Path(str(project.get("background") or ""))
    background = raw_path if raw_path.is_absolute() else project_path.parent / raw_path
    background = background.resolve()
    if not background.exists():
        raise FileNotFoundError(f"Background image not found: {background}")
    return background


def mask_from_shape(shape: dict[str, Any], size: tuple[int, int]) -> Image.Image:
    mask = Image.new("L", size, 0)
    draw = ImageDraw.Draw(mask)
    shape_type = str(shape.get("type") or "").lower()
    if shape_type == "polygon":
        points = [
            (float(point["x"]), float(point["y"]))
            for point in shape.get("points", [])
            if "x" in point and "y" in point
        ]
        if len(points) < 3:
            raise ValueError("Polygon must contain at least three points")
        draw.polygon(points, fill=255)
        return mask

    x = float(shape.get("x", 0))
    y = float(shape.get("y", 0))
    width = float(shape.get("width", 0))
    height = float(shape.get("height", 0))
    if width <= 0 or height <= 0:
        raise ValueError("Shape must have positive width and height")
    box = (x, y, x + width, y + height)
    if shape_type == "circle":
        draw.ellipse(box, fill=255)
    else:
        draw.rectangle(box, fill=255)
    return mask


def find_shape_card(project: dict[str, Any], shape_id: int) -> dict[str, Any]:
    """Return the saved effect card for a shape, or an empty mapping."""
    for card in project.get("shape_cards", []):
        try:
            card_id = int(card.get("id"))
        except (AttributeError, TypeError, ValueError):
            continue
        if card_id == shape_id:
            return card
    return {}


def prepare_project_shape(
    project_path: str | Path,
    shape_id: int,
    *,
    output_dir: str | Path | None = None,
    effect_type: str | None = None,
    seed: int = 1,
    direction: tuple[float, float] | None = None,
    pipeline: PreparationPipeline | None = None,
) -> tuple[EffectAssets, Path]:
    path, project = load_project(project_path)
    requested_id = int(shape_id)
    shape = next(
        (item for item in project.get("shapes", []) if int(item.get("id", -1)) == requested_id),
        None,
    )
    if shape is None:
        raise KeyError(f"Shape id={requested_id} not found")

    background_path = resolve_background_path(path, project)
    with Image.open(background_path) as source:
        image = source.convert("RGB")
    rough_mask = mask_from_shape(shape, image.size)
    card = find_shape_card(project, requested_id)
    resolved_effect = str(effect_type or card.get("tool_type") or "water").lower()
    target = Path(output_dir) if output_dir else path.parent / "effect_assets" / f"shape_{requested_id}"

    preparer = pipeline or PreparationPipeline()
    assets = preparer.prepare(
        image,
        rough_mask,
        effect_type=resolved_effect,
        seed=int(seed),
        direction=direction,
        metadata={
            "project": path.name,
            "shape_id": requested_id,
            "background": background_path.name,
        },
    )
    EffectAssetStore.save(assets, target)
    return assets, target
