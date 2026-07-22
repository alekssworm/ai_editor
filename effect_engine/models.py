from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np


ASSET_VERSION = 2


@dataclass(slots=True)
class StyleProfile:
    palette: tuple[str, ...] = ()
    brightness: float = 0.5
    contrast: float = 0.5
    edge_softness: float = 0.5
    grain: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "palette": list(self.palette),
            "brightness": float(self.brightness),
            "contrast": float(self.contrast),
            "edge_softness": float(self.edge_softness),
            "grain": float(self.grain),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "StyleProfile":
        data = data or {}
        return cls(
            palette=tuple(str(color) for color in data.get("palette", [])),
            brightness=float(data.get("brightness", 0.5)),
            contrast=float(data.get("contrast", 0.5)),
            edge_softness=float(data.get("edge_softness", 0.5)),
            grain=float(data.get("grain", 0.0)),
        )


@dataclass(slots=True)
class EffectAssets:
    effect_type: str
    seed: int
    mask: np.ndarray
    depth: np.ndarray
    flow: np.ndarray
    speed: np.ndarray | None = None
    obstacles: np.ndarray | None = None
    foam: np.ndarray | None = None
    style: StyleProfile = field(default_factory=StyleProfile)
    textures: dict[str, str] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
    version: int = ASSET_VERSION

    def __post_init__(self) -> None:
        self.effect_type = str(self.effect_type).strip().lower()
        self.seed = int(self.seed)
        source_version = int(self.version)
        self.mask = np.clip(np.asarray(self.mask, dtype=np.float32), 0.0, 1.0)
        self.depth = np.clip(np.asarray(self.depth, dtype=np.float32), 0.0, 1.0)
        self.flow = np.asarray(self.flow, dtype=np.float32)
        flow_length = np.linalg.norm(self.flow, axis=-1)
        if self.speed is None:
            self.speed = np.clip(flow_length, 0.0, 1.0).astype(np.float32)
        else:
            self.speed = np.clip(
                np.asarray(self.speed, dtype=np.float32), 0.0, 1.0
            )
        safe_length = np.maximum(flow_length[..., None], 1e-6)
        self.flow = np.where(
            flow_length[..., None] > 1e-6,
            self.flow / safe_length,
            0.0,
        ).astype(np.float32)
        self.obstacles = self._optional_map(self.obstacles)
        self.foam = self._optional_map(self.foam)
        # Version 1 encoded speed in flow magnitude. Construction performs the
        # migration in memory, while the next save writes the version 2 maps.
        if source_version not in (1, ASSET_VERSION):
            raise ValueError(f"Unsupported EffectAssets version: {source_version}")
        self.version = ASSET_VERSION
        self.validate()

    def _optional_map(self, value: np.ndarray | None) -> np.ndarray:
        if value is None:
            return np.zeros(self.mask.shape, dtype=np.float32)
        return np.clip(np.asarray(value, dtype=np.float32), 0.0, 1.0)

    @property
    def height(self) -> int:
        return int(self.mask.shape[0])

    @property
    def width(self) -> int:
        return int(self.mask.shape[1])

    @property
    def size(self) -> tuple[int, int]:
        return self.width, self.height

    def validate(self) -> None:
        if not self.effect_type:
            raise ValueError("effect_type cannot be empty")
        if self.version != ASSET_VERSION:
            raise ValueError(f"Unsupported EffectAssets version: {self.version}")
        if self.mask.ndim != 2:
            raise ValueError("mask must have shape (height, width)")
        if self.depth.shape != self.mask.shape:
            raise ValueError("depth must have the same shape as mask")
        if self.flow.shape != (*self.mask.shape, 2):
            raise ValueError("flow must have shape (height, width, 2)")
        for name in ("speed", "obstacles", "foam"):
            if getattr(self, name).shape != self.mask.shape:
                raise ValueError(f"{name} must have the same shape as mask")
        for name, value in (
            ("mask", self.mask),
            ("depth", self.depth),
            ("flow", self.flow),
            ("speed", self.speed),
            ("obstacles", self.obstacles),
            ("foam", self.foam),
        ):
            if not np.isfinite(value).all():
                raise ValueError(f"{name} contains non-finite values")

    def manifest(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "effect_type": self.effect_type,
            "seed": self.seed,
            "size": {"width": self.width, "height": self.height},
            "style": self.style.to_dict(),
            "textures": dict(self.textures),
            "metadata": dict(self.metadata),
            "files": {
                "mask": "mask.png",
                "depth": "depth.png",
                "flow": "flow.npz",
                "speed": "speed.png",
                "obstacles": "obstacles.png",
                "foam": "foam.png",
            },
        }
