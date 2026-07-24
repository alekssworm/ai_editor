from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol

import numpy as np
from PIL import Image

from .color import linear_to_srgb_u8, srgb_u8_to_linear
from .context import EffectContext


@dataclass(slots=True)
class EffectFrame:
    """Mutable frame state passed through an effect's ordered layer stack."""

    original: np.ndarray
    current: np.ndarray
    data: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_image(cls, image: Image.Image | np.ndarray) -> "EffectFrame":
        if isinstance(image, Image.Image):
            rgb = np.asarray(image.convert("RGB"), dtype=np.uint8)
        else:
            rgb = np.asarray(image)
            if rgb.ndim != 3 or rgb.shape[2] not in (3, 4):
                raise ValueError("image must be RGB/RGBA")
            rgb = rgb[..., :3]
        linear = srgb_u8_to_linear(rgb)
        return cls(original=linear.copy(), current=linear.copy())

    def to_image(self) -> Image.Image:
        return Image.fromarray(
            linear_to_srgb_u8(self.current),
            mode="RGB",
        )

    def begin_effect(self) -> None:
        """Freeze the previous pass as this effect's unmodified source."""
        self.original = self.current.copy()
        self.data.clear()


class EffectLayer(Protocol):
    name: str

    def apply(self, frame: EffectFrame, context: EffectContext) -> None: ...


class LayeredEffect:
    """Base renderer for deterministic effects assembled from small layers."""

    effect_type: str

    def __init__(self, layers: tuple[EffectLayer, ...]) -> None:
        self.layers = tuple(layers)

    @property
    def layer_names(self) -> tuple[str, ...]:
        return tuple(layer.name for layer in self.layers)

    def render(
        self,
        image: Image.Image | np.ndarray,
        context: EffectContext,
    ) -> Image.Image:
        frame = EffectFrame.from_image(image)
        self.apply(frame, context)
        return frame.to_image()

    def apply(self, frame: EffectFrame, context: EffectContext) -> None:
        if context.assets.effect_type.lower() != self.effect_type.lower():
            raise ValueError(
                f"Assets for {context.assets.effect_type!r} cannot be rendered as "
                f"{self.effect_type!r}"
            )
        if frame.current.shape[:2] != context.mask.shape:
            raise ValueError("image and effect maps must have matching dimensions")
        for layer in self.layers:
            layer.apply(frame, context)
