from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Mapping

import numpy as np

from .models import EffectAssets


@dataclass(frozen=True, slots=True)
class EffectContext:
    """Immutable per-frame inputs shared by every deterministic effect layer."""

    time: float
    seed: int
    assets: EffectAssets
    params: Mapping[str, float] = field(default_factory=dict)

    def __post_init__(self) -> None:
        normalized_time = float(self.time) % 1.0
        if not math.isfinite(normalized_time):
            raise ValueError("effect time must be finite")
        normalized_params: dict[str, float] = {}
        for raw_name, raw_value in self.params.items():
            try:
                value = float(raw_value)
            except (TypeError, ValueError) as error:
                raise ValueError(f"Invalid effect parameter {raw_name!r}") from error
            if not math.isfinite(value):
                raise ValueError(f"Effect parameter {raw_name!r} must be finite")
            normalized_params[str(raw_name)] = value
        object.__setattr__(self, "time", normalized_time)
        object.__setattr__(self, "seed", int(self.seed))
        object.__setattr__(self, "params", MappingProxyType(normalized_params))

    @property
    def mask(self) -> np.ndarray:
        return self.assets.mask

    @property
    def depth(self) -> np.ndarray:
        return self.assets.depth

    @property
    def flow(self) -> np.ndarray:
        return self.assets.flow

    @property
    def speed(self) -> np.ndarray:
        return self.assets.speed

    @property
    def obstacles(self) -> np.ndarray:
        return self.assets.obstacles

    @property
    def foam(self) -> np.ndarray:
        return self.assets.foam

    def phase(self, cycles: float = 1.0, offset: float = 0.0) -> float:
        return math.tau * (self.time * float(cycles) + float(offset))

    def rng(self, namespace: str = "default") -> np.random.Generator:
        """Return a stable namespaced RNG without depending on Python's hash()."""
        token = f"{self.seed}:{self.assets.effect_type}:{namespace}".encode("utf-8")
        digest = hashlib.blake2b(token, digest_size=8).digest()
        return np.random.default_rng(int.from_bytes(digest, "little", signed=False))
