from __future__ import annotations

from pathlib import Path
from typing import Mapping

import imageio.v2 as imageio
import numpy as np
from PIL import Image

from .effects.base import EffectRenderer
from .effects.water import WaterFlowEffect
from .models import EffectAssets


class DeterministicEffectEngine:
    def __init__(self) -> None:
        self._effects: dict[str, EffectRenderer] = {}
        self.register(WaterFlowEffect())

    def register(self, effect: EffectRenderer) -> None:
        self._effects[effect.effect_type.lower()] = effect

    def render_frame(
        self,
        image: Image.Image | np.ndarray,
        assets: EffectAssets,
        t: float,
        params: Mapping[str, float] | None = None,
    ) -> Image.Image:
        try:
            renderer = self._effects[assets.effect_type]
        except KeyError as error:
            raise ValueError(f"No renderer registered for effect '{assets.effect_type}'") from error
        return renderer.render(image, assets, t, params=params)

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
        params: Mapping[str, float] | None = None,
    ) -> Path:
        if fps <= 0:
            raise ValueError("fps must be positive")
        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)
        frames = self.render_frames(image, assets, frame_count, params=params)
        writer = imageio.get_writer(
            output,
            fps=int(fps),
            codec="libx264",
            pixelformat="yuv420p",
            macro_block_size=1,
        )
        try:
            for frame in frames:
                writer.append_data(np.asarray(frame.convert("RGB"), dtype=np.uint8))
        finally:
            writer.close()
        return output
