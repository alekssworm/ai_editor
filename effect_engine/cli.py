from __future__ import annotations

import argparse
from pathlib import Path
from typing import Mapping

from PIL import Image

from .models import EffectAssets
from .project import load_project, prepare_project_shape, resolve_background_path
from .preset_registry import default_preset_registry
from .renderer import DeterministicEffectEngine
from .storage import EffectAssetStore


def _direction(value: str) -> tuple[float, float]:
    try:
        x_text, y_text = value.split(",", 1)
        return float(x_text), float(y_text)
    except ValueError as error:
        raise argparse.ArgumentTypeError("direction must be formatted as x,y") from error


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Prepare and render deterministic effect assets")
    commands = parser.add_subparsers(dest="command", required=True)

    prepare = commands.add_parser("prepare", help="Prepare EffectAssets from a shapes.json layer")
    prepare.add_argument("--project", required=True)
    prepare.add_argument("--shape-id", required=True, type=int)
    prepare.add_argument("--output")
    prepare.add_argument("--effect", default=None)
    prepare.add_argument("--preset", default=None)
    prepare.add_argument("--seed", type=int, default=1)
    prepare.add_argument("--direction", type=_direction, default=None)

    render = commands.add_parser("render", help="Render a seamless MP4 from saved EffectAssets")
    render.add_argument("--project", required=True)
    render.add_argument("--assets", required=True)
    render.add_argument("--output", required=True)
    render.add_argument("--frames", type=int, default=72)
    render.add_argument("--fps", type=int, default=24)
    render.add_argument("--preset", default=None)
    render.add_argument("--strength", type=float, default=None)
    render.add_argument("--opacity", type=float, default=None)
    render.add_argument(
        "--temporal-samples",
        type=int,
        default=2,
        help="Linear-light sub-frame samples per output frame (1-16)",
    )
    render.add_argument(
        "--shutter",
        type=float,
        default=0.5,
        help="Motion-blur shutter as a fraction of one frame (0-1)",
    )

    presets = commands.add_parser("presets", help="List installed effect presets")
    presets.add_argument("--effect", default=None)
    return parser


def resolve_render_params(
    assets: EffectAssets,
    *,
    preset_id: str | None = None,
    strength: float | None = None,
    opacity: float | None = None,
) -> dict[str, float]:
    registry = default_preset_registry()
    metadata_params = assets.metadata.get("renderer_params") or {}
    if preset_id is not None:
        params = dict(registry.resolve(assets.effect_type, preset_id).params)
    elif isinstance(metadata_params, Mapping) and metadata_params:
        params = {str(key): float(value) for key, value in metadata_params.items()}
    elif registry.supports(assets.effect_type):
        saved_preset = assets.metadata.get("preset_id")
        params = dict(registry.resolve(assets.effect_type, saved_preset).params)
    else:
        params = {}

    if strength is not None:
        params["strength"] = float(strength)
    if opacity is not None:
        params["opacity"] = float(opacity)
    return params


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "presets":
        presets = default_preset_registry().list(args.effect)
        for preset in presets:
            marker = " (default)" if preset.is_default else ""
            print(f"{preset.effect_type}/{preset.preset_id}\t{preset.label}{marker}")
        return 0

    if args.command == "prepare":
        _, target = prepare_project_shape(
            args.project,
            args.shape_id,
            output_dir=args.output,
            effect_type=args.effect,
            preset_id=args.preset,
            seed=args.seed,
            direction=args.direction,
        )
        print(Path(target).resolve())
        return 0

    project_path, project = load_project(args.project)
    with Image.open(resolve_background_path(project_path, project)) as source:
        background = source.convert("RGB")
    assets = EffectAssetStore.load(args.assets)
    params = resolve_render_params(
        assets,
        preset_id=args.preset,
        strength=args.strength,
        opacity=args.opacity,
    )
    output = DeterministicEffectEngine().export_mp4(
        background,
        assets,
        args.output,
        frame_count=args.frames,
        fps=args.fps,
        params=params,
        temporal_samples=args.temporal_samples,
        shutter_fraction=args.shutter,
    )
    print(output.resolve())
    return 0
