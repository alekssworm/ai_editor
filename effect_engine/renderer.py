from __future__ import annotations

import os
from collections.abc import Callable
from pathlib import Path
from threading import RLock
from typing import Mapping
from uuid import uuid4

import imageio.v2 as imageio
import numpy as np
from PIL import Image

from .compositor import EffectApplication
from .effects.base import EffectRenderer
from .models import EffectAssets
from .plugins import default_effect_plugin_registry
from .session import RenderSession


class DeterministicEffectEngine:
    def __init__(self) -> None:
        self._effect_factories: dict[str, Callable[[], EffectRenderer]] = {
            plugin.effect_type: plugin.create_renderer
            for plugin in default_effect_plugin_registry().list()
        }
        self._factory_lock = RLock()
        self._default_session = self.create_session()

    def create_session(self) -> RenderSession:
        with self._factory_lock:
            factories = tuple(self._effect_factories.items())
        effects = {}
        for effect_type, factory in factories:
            effect = factory()
            if effect.effect_type.lower() != effect_type:
                raise ValueError(
                    f"Effect factory for '{effect_type}' created "
                    f"'{effect.effect_type}'"
                )
            effects[effect_type] = effect
        return RenderSession(effects)

    def register(
        self,
        effect: EffectRenderer,
        *,
        factory: Callable[[], EffectRenderer] | None = None,
    ) -> None:
        """Register a custom effect and its factory for future isolated sessions."""
        effect_type = effect.effect_type.lower()
        with self._factory_lock:
            self._effect_factories[effect_type] = factory or type(effect)
        self._default_session.register(effect)

    def render_frame(
        self,
        image: Image.Image | np.ndarray,
        assets: EffectAssets,
        t: float,
        params: Mapping[str, float] | None = None,
    ) -> Image.Image:
        return self._default_session.render_frame(image, assets, t, params=params)

    def render_composite_frame(
        self,
        image: Image.Image | np.ndarray,
        applications: list[EffectApplication] | tuple[EffectApplication, ...],
        t: float,
    ) -> Image.Image:
        return self._default_session.render_composite_frame(image, applications, t)

    def render_composite_frames(
        self,
        image: Image.Image | np.ndarray,
        applications: list[EffectApplication] | tuple[EffectApplication, ...],
        frame_count: int,
    ) -> list[Image.Image]:
        return self.create_session().render_composite_frames(
            image,
            applications,
            frame_count,
        )

    def render_frames(
        self,
        image: Image.Image | np.ndarray,
        assets: EffectAssets,
        frame_count: int,
        params: Mapping[str, float] | None = None,
    ) -> list[Image.Image]:
        return self.create_session().render_frames(
            image,
            assets,
            frame_count,
            params=params,
        )

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
        session = self.create_session()
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
                frame = session.render_composite_frame(
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
