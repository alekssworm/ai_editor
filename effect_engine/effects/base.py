from __future__ import annotations

from typing import Mapping, Protocol

import numpy as np
from PIL import Image

from ..models import EffectAssets


class EffectRenderer(Protocol):
    effect_type: str

    def render(
        self,
        image: Image.Image | np.ndarray,
        assets: EffectAssets,
        t: float,
        params: Mapping[str, float] | None = None,
    ) -> Image.Image: ...
