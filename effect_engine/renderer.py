from __future__ import annotations

import os
from pathlib import Path
from typing import Mapping
from uuid import uuid4

import imageio.v2 as imageio
import numpy as np
from PIL import Image

from .compositor import EffectApplication, EffectCompositor
from .effects.base import EffectRenderer
from .models import EffectAssets
from .plugins import default_effect_plugin_registry


class DeterministicEffectEngine:
    def __init__(self) -> None:
        self._effects: dict[str, EffectRenderer] = {}
        for plugin in default_effect_plugin_registry().list():
            self.register(plugin.create_renderer())
        self._compositor = EffectCompositor(self._effects)

    def register(self, effect: EffectRenderer) -> None:
        self._effects[effect.effect_type.lower()] = effect

    def render_frame(
        self,
        image: Image.Image | np.ndarray,
        assets: EffectAssets,
        t: float,
        params: Mapping[str, float] | None = None,
    ) -> Image.Image:
        return self._compositor.compose(
            image,
            (EffectApplication(assets=assets, params=params or {}),),
            t,
        )

    def render_composite_frame(
        self,
        image: Image.Image | np.ndarray,
        applications: list[EffectApplication] | tuple[EffectApplication, ...],
        t: float,
    ) -> Image.Image:
        return self._compositor.compose(image, applications, t)

    def render_composite_frames(
        self,
        image: Image.Image | np.ndarray,
        applications: list[EffectApplication] | tuple[EffectApplication, ...],
        frame_count: int,
    ) -> list[Image.Image]:
        if frame_count < 2:
            raise ValueError("frame_count must be at least 2")
        return [
            self.render_composite_frame(
                image,
                applications,
                frame_index / frame_count,
            )
            for frame_index in range(frame_count)
        ]

    def render_frames(
        self,
        image: Image.Image | np.ndarray,
        assets: EffectAssets,
        frame_count: int,
        params: Mapping[str, float] | None = None,
    ) -> list[Image.Image]:
        if frame_count < 2:
            raise ValueError("frame_count must be at least 2")
        # Do not duplicate t=1; after the last frame playback returns to t=0.
        return [
            self.render_frame(image, assets, frame_index / frame_count, params=params)
            for frame_index in range(frame_count)
        ]

    def export_mp4(
        self,
        image: Image.Image | np.ndarray,
        assets: EffectAssets,
        output_path: str | Path,
        *,
        frame_count: int = 72,
        fps: int = 24,
        crf: int = 18,
        params: Mapping[str, float] | None = None,
    ) -> Path:
        return self.export_composite_mp4(
            image,
            (EffectApplication(assets=assets, params=params or {}),),
            output_path,
            frame_count=frame_count,
            fps=fps,
            crf=crf,
        )

    def export_composite_mp4(
        self,
        image: Image.Image | np.ndarray,
        applications: list[EffectApplication] | tuple[EffectApplication, ...],
        output_path: str | Path,
        *,
        frame_count: int = 72,
        fps: int = 24,
        crf: int = 18,
    ) -> Path:
        if fps <= 0:
            raise ValueError("fps must be positive")
        if frame_count < 2:
            raise ValueError("frame_count must be at least 2")
        if not 0 <= int(crf) <= 51:
            raise ValueError("crf must be between 0 and 51")
        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)
        temporary = output.with_name(
            f".{output.stem}-{uuid4().hex}.tmp{output.suffix or '.mp4'}"
        )
        writer = None
        try:
            writer = imageio.get_writer(
                temporary,
                fps=int(fps),
                format="FFMPEG",
                codec="libx264",
                pixelformat="yuv420p",
                # yuv420p needs even dimensions; at most one edge pixel is added.
                macro_block_size=2,
                quality=None,
                ffmpeg_params=[
                    "-crf",
                    str(int(crf)),
                    "-preset",
                    "medium",
                    "-movflags",
                    "+faststart",
                ],
            )
            for frame_index in range(int(frame_count)):
                frame = self.render_composite_frame(
                    image,
                    applications,
                    frame_index / int(frame_count),
                )
                writer.append_data(np.asarray(frame.convert("RGB"), dtype=np.uint8))
            writer.close()
            writer = None
            os.replace(temporary, output)
        finally:
            if writer is not None:
                writer.close()
            temporary.unlink(missing_ok=True)
        return output
