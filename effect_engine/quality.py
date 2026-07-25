from __future__ import annotations

import time
import tracemalloc
from dataclasses import asdict, dataclass
from threading import RLock
from typing import Mapping

import numpy as np
from PIL import Image

from .models import EffectAssets
from .renderer import DeterministicEffectEngine


_QUALITY_MEASUREMENT_LOCK = RLock()


def _rgb_array(image: Image.Image | np.ndarray) -> np.ndarray:
    if isinstance(image, Image.Image):
        return np.asarray(image.convert("RGB"), dtype=np.uint8)
    value = np.asarray(image)
    if value.ndim != 3 or value.shape[2] not in (3, 4):
        raise ValueError("image must be RGB or RGBA")
    return np.asarray(value[..., :3], dtype=np.uint8)


def _rmse(first: np.ndarray, second: np.ndarray) -> float:
    delta = first.astype(np.float32) - second.astype(np.float32)
    return float(np.sqrt(np.mean(delta * delta)))


@dataclass(frozen=True, slots=True)
class EffectQualityReport:
    effect_type: str
    frame_count: int
    determinism_max_error: int
    outside_mask_max_error: int
    loop_seam_rmse: float
    median_transition_rmse: float
    loop_seam_ratio: float
    average_frame_ms: float
    python_peak_memory_mb: float

    @property
    def passed(self) -> bool:
        return (
            self.determinism_max_error == 0
            and self.outside_mask_max_error == 0
            and self.loop_seam_ratio <= 1.8
        )

    def to_dict(self) -> dict[str, object]:
        return {**asdict(self), "passed": self.passed}


def analyze_effect_quality(
    image: Image.Image | np.ndarray,
    assets: EffectAssets,
    *,
    params: Mapping[str, float] | None = None,
    frame_count: int = 12,
    engine: DeterministicEffectEngine | None = None,
) -> EffectQualityReport:
    """Measure loop continuity, repeatability, masking, time and Python memory."""
    if frame_count < 4:
        raise ValueError("frame_count must be at least 4")
    renderer = engine or DeterministicEffectEngine()
    source = _rgb_array(image)
    session = renderer.create_session()
    with _QUALITY_MEASUREMENT_LOCK:
        tracing_before = tracemalloc.is_tracing()
        if not tracing_before:
            tracemalloc.start()
        tracemalloc.reset_peak()
        started = time.perf_counter()
        try:
            frames = [
                np.asarray(
                    session.render_frame(
                        image,
                        assets,
                        index / frame_count,
                        params=params,
                    ),
                    dtype=np.uint8,
                )
                for index in range(frame_count)
            ]
            deterministic_a = np.asarray(
                session.render_frame(image, assets, 0.371, params=params),
                dtype=np.uint8,
            )
            deterministic_b = np.asarray(
                session.render_frame(image, assets, 0.371, params=params),
                dtype=np.uint8,
            )
            elapsed = time.perf_counter() - started
            _, peak_bytes = tracemalloc.get_traced_memory()
        finally:
            if not tracing_before:
                tracemalloc.stop()

    transitions = [
        _rmse(frames[index], frames[index + 1])
        for index in range(frame_count - 1)
    ]
    seam = _rmse(frames[-1], frames[0])
    median_transition = float(np.median(transitions))
    if median_transition <= 1e-8:
        seam_ratio = 0.0 if seam <= 1e-8 else float("inf")
    else:
        seam_ratio = seam / median_transition
    outside = assets.mask <= 1e-4
    outside_error = 0
    if np.any(outside):
        for frame in frames:
            outside_error = max(
                outside_error,
                int(
                    np.abs(frame.astype(np.int16) - source.astype(np.int16))[
                        outside
                    ].max(initial=0)
                ),
            )
    determinism_error = int(
        np.abs(
            deterministic_a.astype(np.int16) - deterministic_b.astype(np.int16)
        ).max(initial=0)
    )
    return EffectQualityReport(
        effect_type=assets.effect_type,
        frame_count=frame_count,
        determinism_max_error=determinism_error,
        outside_mask_max_error=outside_error,
        loop_seam_rmse=seam,
        median_transition_rmse=median_transition,
        loop_seam_ratio=seam_ratio,
        average_frame_ms=elapsed * 1000.0 / (frame_count + 2),
        python_peak_memory_mb=peak_bytes / (1024.0 * 1024.0),
    )
