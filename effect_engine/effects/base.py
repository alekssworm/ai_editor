from __future__ import annotations

from typing import Protocol

import numpy as np
from PIL import Image

from ..context import EffectContext
from ..layers import EffectFrame


class EffectRenderer(Protocol):
    effect_type: str

    def render(
        self,
        image: Image.Image | np.ndarray,
        context: EffectContext,
    ) -> Image.Image: ...

    def apply(self, frame: EffectFrame, context: EffectContext) -> None: ...
