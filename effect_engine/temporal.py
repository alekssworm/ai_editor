from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class TemporalSampling:
    """Deterministic sub-frame sample positions for linear-light motion blur."""

    samples: int = 1
    shutter: float = 0.0

    def __post_init__(self) -> None:
        raw_samples = self.samples
        samples = int(raw_samples)
        shutter = float(self.shutter)
        if samples != raw_samples:
            raise ValueError("temporal samples must be an integer")
        if not 1 <= samples <= 16:
            raise ValueError("temporal samples must be between 1 and 16")
        if not math.isfinite(shutter) or not 0.0 <= shutter <= 1.0:
            raise ValueError("normalized shutter must be between 0 and 1")
        object.__setattr__(self, "samples", samples)
        object.__setattr__(self, "shutter", shutter)

    @classmethod
    def for_frame(
        cls,
        *,
        samples: int,
        shutter_fraction: float,
        frame_count: int,
    ) -> "TemporalSampling":
        if frame_count < 2:
            raise ValueError("frame_count must be at least 2")
        fraction = float(shutter_fraction)
        if not math.isfinite(fraction) or not 0.0 <= fraction <= 1.0:
            raise ValueError("shutter_fraction must be between 0 and 1")
        return cls(samples=samples, shutter=fraction / int(frame_count))

    def times(self, time: float) -> tuple[float, ...]:
        center = float(time)
        if not math.isfinite(center):
            raise ValueError("effect time must be finite")
        center %= 1.0
        if self.samples == 1 or self.shutter <= 0.0:
            return (center,)
        return tuple(
            (
                center
                + (((index + 0.5) / self.samples) - 0.5) * self.shutter
            )
            % 1.0
            for index in range(self.samples)
        )
