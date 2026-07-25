from __future__ import annotations

import math

import numpy as np


def periodic_sine(
    spatial_phase: np.ndarray,
    loop_phase: float,
    *,
    temporal_cycles: int = 1,
    offset: float = 0.0,
) -> np.ndarray:
    """Return a sine field whose temporal component closes exactly at t=1."""
    cycles = int(temporal_cycles)
    if cycles != temporal_cycles:
        raise ValueError("temporal_cycles must be an integer")
    return np.sin(
        np.asarray(spatial_phase, dtype=np.float32)
        - np.float32(loop_phase) * cycles
        + np.float32(offset)
    )


def reflect_coordinates(values: np.ndarray, size: int) -> np.ndarray:
    """Fold sampling coordinates at image edges without allocating a padded image."""
    if size <= 1:
        return np.zeros_like(values, dtype=np.float32)
    maximum = float(size - 1)
    period = maximum * 2.0
    folded = np.mod(values, period)
    return np.where(folded <= maximum, folded, period - folded).astype(np.float32)


def bilinear_remap(
    image: np.ndarray,
    map_x: np.ndarray,
    map_y: np.ndarray,
    *,
    tile_rows: int = 192,
) -> np.ndarray:
    """Sample a float image using reflected coordinates and bounded row tiles."""
    source = np.asarray(image, dtype=np.float32)
    if source.ndim not in (2, 3):
        raise ValueError("image must have shape (height, width[, channels])")
    map_x, map_y = np.broadcast_arrays(
        np.asarray(map_x, dtype=np.float32),
        np.asarray(map_y, dtype=np.float32),
    )
    height, width = source.shape[:2]
    has_channels = source.ndim == 3
    output_shape = map_x.shape + ((source.shape[2],) if has_channels else ())
    output = np.empty(output_shape, dtype=np.float32)
    rows = max(1, int(tile_rows))
    for row_start in range(0, map_x.shape[0], rows):
        row_end = min(map_x.shape[0], row_start + rows)
        x = reflect_coordinates(map_x[row_start:row_end], width)
        y = reflect_coordinates(map_y[row_start:row_end], height)
        x0 = np.floor(x).astype(np.int32)
        y0 = np.floor(y).astype(np.int32)
        x1 = np.minimum(x0 + 1, width - 1)
        y1 = np.minimum(y0 + 1, height - 1)
        weight_x = x - x0
        weight_y = y - y0
        if has_channels:
            weight_x = weight_x[..., None]
            weight_y = weight_y[..., None]
        top = source[y0, x0] * (1.0 - weight_x) + source[y0, x1] * weight_x
        bottom = source[y1, x0] * (1.0 - weight_x) + source[y1, x1] * weight_x
        output[row_start:row_end] = top * (1.0 - weight_y) + bottom * weight_y
    return output


def integrated_flow_coordinates(
    flow_x: np.ndarray,
    flow_y: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    """Build continuous approximate streamline coordinates from a dense flow."""
    flow_x = np.asarray(flow_x, dtype=np.float32)
    flow_y = np.asarray(flow_y, dtype=np.float32)
    if flow_x.shape != flow_y.shape or flow_x.ndim != 2:
        raise ValueError("flow components must be matching two-dimensional arrays")
    height, width = flow_x.shape
    center_x = width // 2
    center_y = height // 2
    along = np.cumsum(flow_x, axis=1, dtype=np.float32)
    along -= along[:, center_x : center_x + 1]
    row_offsets = np.cumsum(flow_y[:, center_x], dtype=np.float32)
    row_offsets -= row_offsets[center_y]
    along += row_offsets[:, None]
    across = np.cumsum(-flow_y, axis=0, dtype=np.float32)
    across -= across[center_y : center_y + 1, :]
    column_offsets = np.cumsum(flow_x[center_y, :], dtype=np.float32)
    column_offsets -= column_offsets[center_x]
    across += column_offsets[None, :]
    return along, across


def _box_sizes_for_gaussian(sigma: float, passes: int = 3) -> tuple[int, ...]:
    ideal = math.sqrt((12.0 * sigma * sigma / passes) + 1.0)
    lower = int(math.floor(ideal))
    if lower % 2 == 0:
        lower -= 1
    lower = max(1, lower)
    upper = lower + 2
    numerator = 12.0 * sigma * sigma - passes * lower * lower - 4 * passes * lower
    count_lower = int(round((numerator - 3 * passes) / (-4 * lower - 4)))
    count_lower = max(0, min(passes, count_lower))
    return tuple(
        lower if index < count_lower else upper for index in range(passes)
    )


def _box_blur_axis(value: np.ndarray, radius: int, axis: int) -> np.ndarray:
    if radius <= 0 or value.shape[axis] <= 1:
        return value.astype(np.float32, copy=True)
    pad_width = [(0, 0)] * value.ndim
    pad_width[axis] = (radius, radius)
    padded = np.pad(value, pad_width, mode="edge")
    cumulative = np.cumsum(padded, axis=axis, dtype=np.float32)
    zero_shape = list(cumulative.shape)
    zero_shape[axis] = 1
    cumulative = np.concatenate(
        (np.zeros(zero_shape, dtype=np.float32), cumulative),
        axis=axis,
    )
    window = radius * 2 + 1
    high = [slice(None)] * value.ndim
    low = [slice(None)] * value.ndim
    high[axis] = slice(window, window + value.shape[axis])
    low[axis] = slice(0, value.shape[axis])
    return (
        cumulative[tuple(high)] - cumulative[tuple(low)]
    ) / np.float32(window)


def gaussian_blur_float(value: np.ndarray, radius: float) -> np.ndarray:
    """Approximate a Gaussian in float32 without 8-bit map quantization."""
    source = np.asarray(value, dtype=np.float32)
    if source.ndim not in (2, 3):
        raise ValueError("value must have shape (height, width[, channels])")
    sigma = max(0.0, float(radius))
    if sigma <= 1e-4:
        return source.copy()
    result = source.copy()
    for size in _box_sizes_for_gaussian(sigma):
        box_radius = (size - 1) // 2
        result = _box_blur_axis(result, box_radius, 1)
        result = _box_blur_axis(result, box_radius, 0)
    return result.astype(np.float32, copy=False)
