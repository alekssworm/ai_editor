from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image

from .project import load_project, prepare_project_shape, resolve_background_path
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
    prepare.add_argument("--seed", type=int, default=1)
    prepare.add_argument("--direction", type=_direction, default=None)

    render = commands.add_parser("render", help="Render a seamless MP4 from saved EffectAssets")
    render.add_argument("--project", required=True)
    render.add_argument("--assets", required=True)
    render.add_argument("--output", required=True)
    render.add_argument("--frames", type=int, default=72)
    render.add_argument("--fps", type=int, default=24)
    render.add_argument("--strength", type=float, default=4.0)
    render.add_argument("--opacity", type=float, default=1.0)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "prepare":
        _, target = prepare_project_shape(
            args.project,
            args.shape_id,
            output_dir=args.output,
            effect_type=args.effect,
            seed=args.seed,
            direction=args.direction,
        )
        print(Path(target).resolve())
        return 0

    project_path, project = load_project(args.project)
    background = Image.open(resolve_background_path(project_path, project)).convert("RGB")
    assets = EffectAssetStore.load(args.assets)
    output = DeterministicEffectEngine().export_mp4(
        background,
        assets,
        args.output,
        frame_count=args.frames,
        fps=args.fps,
        params={"strength": args.strength, "opacity": args.opacity},
    )
    print(output.resolve())
    return 0
