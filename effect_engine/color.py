from __future__ import annotations

import numpy as np


def srgb_to_linear(values: np.ndarray) -> np.ndarray:
    """Convert display-encoded sRGB values in [0, 1] to linear light."""
    srgb = np.clip(np.asarray(values, dtype=np.float32), 0.0, 1.0)
    return np.where(
        srgb <= 0.04045,
        srgb / 12.92,
        ((srgb + 0.055) / 1.055) ** 2.4,
    ).astype(np.float32)


def linear_to_srgb(values: np.ndarray) -> np.ndarray:
    """Convert linear-light values in [0, 1] to display-encoded sRGB."""
    linear = np.clip(np.asarray(values, dtype=np.float32), 0.0, 1.0)
    return np.where(
        linear <= 0.0031308,
        linear * 12.92,
        1.055 * np.power(linear, 1.0 / 2.4) - 0.055,
    ).astype(np.float32)


_SRGB_U8_TO_LINEAR_LUT = srgb_to_linear(
    np.arange(256, dtype=np.float32) / 255.0
)
_LINEAR_TO_SRGB_U8_LUT = np.rint(
    linear_to_srgb(np.linspace(0.0, 1.0, 65_536, dtype=np.float32)) * 255.0
).astype(np.uint8)


def srgb_u8_to_linear(values: np.ndarray) -> np.ndarray:
    array = np.asarray(values)
    if array.dtype == np.uint8:
        return _SRGB_U8_TO_LINEAR_LUT[array]
    return srgb_to_linear(array.astype(np.float32) / 255.0)


def linear_to_srgb_u8(values: np.ndarray) -> np.ndarray:
    linear = np.nan_to_num(
        np.asarray(values, dtype=np.float32),
        nan=0.0,
        posinf=1.0,
        neginf=0.0,
    )
    indices = np.rint(np.clip(linear, 0.0, 1.0) * 65_535.0).astype(np.uint16)
    return _LINEAR_TO_SRGB_U8_LUT[indices]


def srgb_color_to_linear(values: np.ndarray) -> np.ndarray:
    """Convert an RGB color expressed in the legacy 0..255 range."""
    return srgb_u8_to_linear(np.asarray(values, dtype=np.float32))
