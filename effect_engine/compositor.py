from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping

import numpy as np
from PIL import Image

from .context import EffectContext
from .effects.base import EffectRenderer
from .models import EffectAssets


@dataclass(frozen=True, slots=True)
class EffectApplication:
    """One prepared effect pass in a multi-effect composition."""

    assets: EffectAssets
    params: Mapping[str, float] = field(default_factory=dict)


class EffectCompositor:
    """Apply prepared effects in a stable order to one source image."""

    def __init__(self, effects: Mapping[str, EffectRenderer]) -> None:
        self._effects = effects

    def compose(
        self,
        image: Image.Image | np.ndarray,
        applications: list[EffectApplication] | tuple[EffectApplication, ...],
        time: float,
    ) -> Image.Image:
        current = (
            image.convert("RGB")
            if isinstance(image, Image.Image)
            else Image.fromarray(np.asarray(image, dtype=np.uint8)[..., :3], mode="RGB")
        )
        for application in applications:
            effect_type = application.assets.effect_type.lower()
            try:
                renderer = self._effects[effect_type]
            except KeyError as error:
                raise ValueError(
                    f"No renderer registered for effect '{effect_type}'"
                ) from error
            context = EffectContext(
                time=time,
                seed=application.assets.seed,
                assets=application.assets,
                params=application.params,
            )
            current = renderer.render(current, context)
        return current
