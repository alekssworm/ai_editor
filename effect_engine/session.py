from __future__ import annotations

from threading import RLock
from typing import Mapping

import numpy as np
from PIL import Image

from .compositor import EffectApplication, EffectCompositor
from .effects.base import EffectRenderer
from .models import EffectAssets


class RenderSession:
    """Own renderer instances and caches for one preview or export task."""

    def __init__(self, effects: Mapping[str, EffectRenderer]) -> None:
        self._effects = {key.lower(): value for key, value in effects.items()}
        self._compositor = EffectCompositor(self._effects)
        self._lock = RLock()

    def register(self, effect: EffectRenderer) -> None:
        with self._lock:
            self._effects[effect.effect_type.lower()] = effect

    def render_frame(
        self,
        image: Image.Image | np.ndarray,
        assets: EffectAssets,
        t: float,
        params: Mapping[str, float] | None = None,
    ) -> Image.Image:
        return self.render_composite_frame(
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
        with self._lock:
            return self._compositor.compose(image, applications, t)

    def render_frames(
        self,
        image: Image.Image | np.ndarray,
        assets: EffectAssets,
        frame_count: int,
        params: Mapping[str, float] | None = None,
    ) -> list[Image.Image]:
        if frame_count < 2:
            raise ValueError("frame_count must be at least 2")
        return [
            self.render_frame(
                image,
                assets,
                frame_index / frame_count,
                params=params,
            )
            for frame_index in range(frame_count)
        ]

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

