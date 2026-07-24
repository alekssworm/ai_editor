from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Mapping

import numpy as np
from PIL import Image

from .cache import ByteBudgetLRU, CacheInfo, effect_cache_budget_bytes
from .context import EffectContext
from .effects.base import EffectRenderer
from .layers import EffectFrame
from .models import EffectAssets
from .region import EffectRegion, effect_region, effect_region_nbytes


@dataclass(frozen=True, slots=True)
class EffectApplication:
    """One prepared effect pass in a multi-effect composition."""

    assets: EffectAssets
    params: Mapping[str, float] = field(default_factory=dict)


class EffectCompositor:
    """Apply prepared effects in a stable order to one source image."""

    def __init__(self, effects: Mapping[str, EffectRenderer]) -> None:
        self._effects = effects
        self._region_cache: ByteBudgetLRU[
            tuple[int, int, int, int], EffectRegion | None
        ] = ByteBudgetLRU(
            effect_cache_budget_bytes(),
            size_of=effect_region_nbytes,
        )

    @staticmethod
    def _roi_enabled() -> bool:
        return os.environ.get("AI_EDITOR_EFFECT_ROI", "1").strip().lower() not in {
            "0",
            "false",
            "no",
        }

    @staticmethod
    def _roi_margin() -> int:
        try:
            return max(
                0,
                min(
                    512,
                    int(os.environ.get("AI_EDITOR_EFFECT_ROI_MARGIN", "96")),
                ),
            )
        except ValueError:
            return 96

    def _region_for(
        self,
        assets: EffectAssets,
        image_size: tuple[int, int],
    ) -> EffectRegion | None:
        if assets.size != image_size:
            raise ValueError("image and effect maps must have matching dimensions")
        margin = self._roi_margin()
        key = (assets.cache_token, id(assets), margin, assets.version)
        return self._region_cache.get_or_create(
            key,
            lambda: effect_region(assets, margin=margin),
        )

    def region_cache_info(self) -> CacheInfo:
        return self._region_cache.info()

    def compose(
        self,
        image: Image.Image | np.ndarray,
        applications: list[EffectApplication] | tuple[EffectApplication, ...],
        time: float,
    ) -> Image.Image:
        # ROI composition never reads the full-size ``original`` buffer. Avoid
        # retaining a second 4K float image; each active region gets its own
        # immutable source copy immediately before the effect is applied.
        frame = EffectFrame.from_image(image, copy_original=False)
        for application in applications:
            effect_type = application.assets.effect_type.lower()
            try:
                renderer = self._effects[effect_type]
            except KeyError as error:
                raise ValueError(
                    f"No renderer registered for effect '{effect_type}'"
                ) from error
            if self._roi_enabled():
                region = self._region_for(
                    application.assets,
                    (frame.current.shape[1], frame.current.shape[0]),
                )
            else:
                if application.assets.size != (
                    frame.current.shape[1],
                    frame.current.shape[0],
                ):
                    raise ValueError(
                        "image and effect maps must have matching dimensions"
                    )
                region = EffectRegion(
                    0,
                    0,
                    application.assets.width,
                    application.assets.height,
                    application.assets,
                    borrowed_assets=True,
                )
            if region is None:
                continue
            context = EffectContext(
                time=time,
                seed=region.assets.seed,
                assets=region.assets,
                params=application.params,
            )
            y_slice, x_slice = region.slices
            source = frame.current[y_slice, x_slice].copy()
            region_frame = EffectFrame(
                original=source,
                current=source.copy(),
            )
            renderer.apply(region_frame, context)
            frame.current[y_slice, x_slice] = region_frame.current
        return frame.to_image()
