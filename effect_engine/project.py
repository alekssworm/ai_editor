from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from PIL import Image, ImageDraw

from .parameters import renderer_params_from_card
from .preset_registry import resolve_card_preset
from .models import EffectAssets
from .preparation import PreparationPipeline
from .storage import EffectAssetStore


PROJECT_SCHEMA_VERSION = 2


def normalize_direction(value: Any) -> tuple[float, float] | None:
    """Parse and normalize a saved direction vector."""
    if isinstance(value, Mapping):
        raw_x = value.get("x", value.get("dx"))
        raw_y = value.get("y", value.get("dy"))
    elif (
        isinstance(value, Sequence)
        and not isinstance(value, (str, bytes))
        and len(value) >= 2
    ):
        raw_x, raw_y = value[0], value[1]
    else:
        return None

    try:
        x, y = float(raw_x), float(raw_y)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(x) or not math.isfinite(y):
        return None
    length = math.hypot(x, y)
    if length < 1e-8:
        return None
    return x / length, y / length


def project_flow_direction(
    project: Mapping[str, Any], shape_id: int
) -> tuple[float, float] | None:
    directions = project.get("flow_directions") or {}
    if isinstance(directions, Mapping):
        raw = directions.get(str(int(shape_id)), directions.get(int(shape_id)))
        parsed = normalize_direction(raw)
        if parsed is not None:
            return parsed

    for shape in project.get("shapes", []):
        try:
            current_id = int(shape.get("id"))
        except (AttributeError, TypeError, ValueError):
            continue
        if current_id == int(shape_id):
            return normalize_direction(shape.get("flow_direction"))
    return None


def serialize_flow_directions(
    directions: Mapping[Any, Any], shape_ids: Iterable[int]
) -> dict[str, dict[str, float]]:
    result: dict[str, dict[str, float]] = {}
    for raw_shape_id in shape_ids:
        shape_id = int(raw_shape_id)
        value = directions.get(shape_id, directions.get(str(shape_id)))
        direction = normalize_direction(value)
        if direction is not None:
            result[str(shape_id)] = {"x": direction[0], "y": direction[1]}
    return result


def load_project(project_path: str | Path) -> tuple[Path, dict[str, Any]]:
    path = Path(project_path).resolve()
    project = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(project, dict):
        raise ValueError("Project root must be a JSON object")
    try:
        schema_version = int(project.get("schema_version", 1))
    except (TypeError, ValueError) as error:
        raise ValueError("Invalid project schema_version") from error
    if schema_version < 1 or schema_version > PROJECT_SCHEMA_VERSION:
        raise ValueError(f"Unsupported project schema_version: {schema_version}")
    return path, project


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
    preset_id: str | None = None,
    seed: int = 1,
    direction: tuple[float, float] | None = None,
    card_override: Mapping[str, Any] | None = None,
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
    card = (
        dict(card_override)
        if card_override is not None
        else find_shape_card(project, requested_id)
    )
    resolved_effect = str(effect_type or card.get("tool_type") or "water").lower()
    preset = resolve_card_preset(card, resolved_effect, preset_id=preset_id)
    renderer_params = renderer_params_from_card(
        card,
        effect_type=resolved_effect,
        preset_id=preset.preset_id if preset is not None else None,
    )
    target = Path(output_dir) if output_dir else path.parent / "effect_assets" / f"shape_{requested_id}"

    resolved_direction = normalize_direction(direction)
    if resolved_direction is None:
        resolved_direction = project_flow_direction(project, requested_id)

    preparer = pipeline or PreparationPipeline()
    assets = preparer.prepare(
        image,
        rough_mask,
        effect_type=resolved_effect,
        seed=int(seed),
        direction=resolved_direction,
        metadata={
            "project": path.name,
            "shape_id": requested_id,
            "background": background_path.name,
            **({"preset_id": preset.preset_id} if preset is not None else {}),
            **({"renderer_params": renderer_params} if renderer_params else {}),
        },
    )
    EffectAssetStore.save(assets, target)
    return assets, target
