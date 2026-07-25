from __future__ import annotations

from threading import RLock
from typing import Mapping

import numpy as np
from PIL import Image

from .compositor import EffectApplication, EffectCompositor
from .cache import CacheInfo
from .color import linear_to_srgb_u8
from .effects.base import EffectRenderer
from .models import EffectAssets
from .temporal import TemporalSampling


class RenderSession:
    """Own renderer instances and caches for one preview or export task."""

    def __init__(self, effects: Mapping[str, EffectRenderer]) -> None:
        self._effects = {key.lower(): value for key, value in effects.items()}
        self._compositor = EffectCompositor(self._effects)
        self._lock = RLock()

    def register(self, effect: EffectRenderer) -> None:
        with self._lock:
            self._effects[effect.effect_type.lower()] = effect

    def region_cache_info(self) -> CacheInfo:
        return self._compositor.region_cache_info()

    def render_frame(
        self,
        image: Image.Image | np.ndarray,
        assets: EffectAssets,
        t: float,
        params: Mapping[str, float] | None = None,
        *,
        temporal_sampling: TemporalSampling | None = None,
    ) -> Image.Image:
        return self.render_composite_frame(
            image,
            (EffectApplication(assets=assets, params=params or {}),),
            t,
            temporal_sampling=temporal_sampling,
        )

    def render_composite_frame(
        self,
        image: Image.Image | np.ndarray,
        applications: list[EffectApplication] | tuple[EffectApplication, ...],
        t: float,
        *,
        temporal_sampling: TemporalSampling | None = None,
    ) -> Image.Image:
        with self._lock:
            sampling = temporal_sampling or TemporalSampling()
            sample_times = sampling.times(t)
            if len(sample_times) == 1:
                return self._compositor.compose(image, applications, sample_times[0])
            accumulated = None
            for sample_time in sample_times:
                current = self._compositor.compose_linear(
                    image,
                    applications,
                    sample_time,
                )
                if accumulated is None:
                    accumulated = current.astype(np.float32, copy=True)
                else:
                    accumulated += current
            averaged = accumulated / np.float32(len(sample_times))
            return Image.fromarray(linear_to_srgb_u8(averaged), mode="RGB")

    def render_frames(
        self,
        image: Image.Image | np.ndarray,
        assets: EffectAssets,
        frame_count: int,
        params: Mapping[str, float] | None = None,
        *,
        temporal_samples: int = 1,
        shutter_fraction: float = 0.0,
    ) -> list[Image.Image]:
        if frame_count < 2:
            raise ValueError("frame_count must be at least 2")
        sampling = TemporalSampling.for_frame(
            samples=temporal_samples,
            shutter_fraction=shutter_fraction,
            frame_count=frame_count,
        )
        return [
            self.render_frame(
                image,
                assets,
                frame_index / frame_count,
                params=params,
                temporal_sampling=sampling,
            )
            for frame_index in range(frame_count)
        ]

    def render_composite_frames(
        self,
        image: Image.Image | np.ndarray,
        applications: list[EffectApplication] | tuple[EffectApplication, ...],
        frame_count: int,
        *,
        temporal_samples: int = 1,
        shutter_fraction: float = 0.0,
    ) -> list[Image.Image]:
        if frame_count < 2:
            raise ValueError("frame_count must be at least 2")
        sampling = TemporalSampling.for_frame(
            samples=temporal_samples,
            shutter_fraction=shutter_fraction,
            frame_count=frame_count,
        )
        return [
            self.render_composite_frame(
                image,
                applications,
                frame_index / frame_count,
                temporal_sampling=sampling,
            )
            for frame_index in range(frame_count)
        ]
