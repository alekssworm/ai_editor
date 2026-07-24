from __future__ import annotations

import os
import time
from dataclasses import dataclass, field
from typing import Any, Mapping, Protocol

import numpy as np
from PIL import Image, ImageFilter

from .models import EffectAssets, StyleProfile


def _rgb_array(image: Image.Image | np.ndarray) -> np.ndarray:
    if isinstance(image, Image.Image):
        return np.asarray(image.convert("RGB"), dtype=np.uint8)
    value = np.asarray(image)
    if value.ndim != 3 or value.shape[2] not in (3, 4):
        raise ValueError("image must be RGB/RGBA")
    return np.asarray(value[..., :3], dtype=np.uint8)


def _mask_array(mask: Image.Image | np.ndarray, size: tuple[int, int]) -> np.ndarray:
    if isinstance(mask, Image.Image):
        value = np.asarray(mask.convert("L"), dtype=np.float32) / 255.0
    else:
        value = np.asarray(mask, dtype=np.float32)
        if value.max(initial=0.0) > 1.0:
            value = value / 255.0
    if value.shape != (size[1], size[0]):
        raise ValueError(f"mask shape {value.shape} does not match image size {size}")
    return np.clip(value, 0.0, 1.0)


class MaskRefiner(Protocol):
    name: str

    def refine(self, image: np.ndarray, rough_mask: np.ndarray) -> np.ndarray: ...


class DepthEstimator(Protocol):
    name: str

    def estimate(self, image: np.ndarray, mask: np.ndarray) -> np.ndarray: ...


class FlowEstimator(Protocol):
    name: str

    def estimate(
        self,
        image: np.ndarray,
        mask: np.ndarray,
        direction: tuple[float, float] | None = None,
        guides: list[dict[str, Any]] | None = None,
    ) -> np.ndarray: ...


class TextureGenerator(Protocol):
    name: str

    def generate(
        self,
        image: np.ndarray,
        mask: np.ndarray,
        effect_type: str,
        seed: int,
        style: StyleProfile,
    ) -> dict[str, str]: ...


@dataclass(slots=True)
class MorphologyMaskRefiner:
    close_radius: int = 2
    feather_radius: float = 2.0
    name: str = "morphology-v1"

    def refine(self, image: np.ndarray, rough_mask: np.ndarray) -> np.ndarray:
        del image
        mask_u8 = np.where(rough_mask >= 0.5, 255, 0).astype(np.uint8)
        result = Image.fromarray(mask_u8, mode="L")
        if self.close_radius > 0:
            size = self.close_radius * 2 + 1
            result = result.filter(ImageFilter.MaxFilter(size=size))
            result = result.filter(ImageFilter.MinFilter(size=size))
        if self.feather_radius > 0:
            result = result.filter(ImageFilter.GaussianBlur(radius=self.feather_radius))
        return np.asarray(result, dtype=np.float32) / 255.0


def _pipeline_array(value: Any, size: tuple[int, int]) -> np.ndarray:
    if hasattr(value, "detach"):
        value = value.detach().cpu().numpy()
    elif hasattr(value, "cpu") and hasattr(value, "numpy"):
        value = value.cpu().numpy()
    array = np.asarray(value)
    array = np.squeeze(array)
    if array.ndim != 2:
        raise ValueError(f"AI map has unsupported shape: {array.shape}")
    if array.shape != (size[1], size[0]):
        array = np.asarray(
            Image.fromarray(array.astype(np.float32), mode="F").resize(
                size, Image.Resampling.BILINEAR
            ),
            dtype=np.float32,
        )
    return np.asarray(array, dtype=np.float32)


@dataclass(slots=True)
class TransformersMaskRefiner:
    """Optional SAM proposal provider, loaded only when AI preparation is enabled."""

    model: str = "facebook/sam-vit-base"
    device: int = -1
    feather_radius: float = 2.0
    name: str = "sam-mask-proposal"
    _pipeline: Any = field(default=None, init=False, repr=False)

    def _load(self):
        if self._pipeline is None:
            try:
                from transformers import pipeline
            except (ImportError, OSError) as error:
                raise RuntimeError(
                    "AI preparation requires PyTorch and Transformers. "
                    "Install the optional packages described in "
                    "effect_engine/README.md."
                ) from error

            try:
                self._pipeline = pipeline(
                    task="mask-generation",
                    model=self.model,
                    device=self.device,
                )
            except (ImportError, OSError) as error:
                raise RuntimeError(
                    f"Could not load mask model {self.model!r}: {error}"
                ) from error
        return self._pipeline

    def refine(self, image: np.ndarray, rough_mask: np.ndarray) -> np.ndarray:
        output = self._load()(Image.fromarray(image, mode="RGB"))
        candidates = output.get("masks", []) if isinstance(output, Mapping) else []
        rough_binary = rough_mask >= 0.35
        best_mask = None
        best_score = 0.0
        for candidate in candidates:
            try:
                proposed = _pipeline_array(
                    candidate, (image.shape[1], image.shape[0])
                ) > 0.5
            except (TypeError, ValueError):
                continue
            intersection = float(np.logical_and(proposed, rough_binary).sum())
            union = float(np.logical_or(proposed, rough_binary).sum())
            score = intersection / max(1.0, union)
            if score > best_score:
                best_score, best_mask = score, proposed
        if best_mask is None or best_score < 0.03:
            return MorphologyMaskRefiner().refine(image, rough_mask)

        corridor = Image.fromarray(
            np.where(rough_binary, 255, 0).astype(np.uint8), mode="L"
        ).filter(ImageFilter.MaxFilter(31))
        corridor_array = np.asarray(corridor, dtype=np.float32) / 255.0
        refined = best_mask.astype(np.float32) * corridor_array
        refined_image = Image.fromarray(
            np.rint(refined * 255.0).astype(np.uint8), mode="L"
        ).filter(ImageFilter.GaussianBlur(radius=self.feather_radius))
        return np.asarray(refined_image, dtype=np.float32) / 255.0


@dataclass(slots=True)
class ProviderRetryState:
    base_delay_seconds: float = 20.0
    max_delay_seconds: float = 300.0
    disabled_reason: str | None = None
    failure_count: int = 0
    next_retry_at: float = 0.0

    def can_attempt(self) -> bool:
        return self.disabled_reason is None or time.monotonic() >= self.next_retry_at

    def failed(self, error: Exception) -> None:
        self.failure_count += 1
        self.disabled_reason = f"{type(error).__name__}: {error}"
        delay = min(
            self.max_delay_seconds,
            self.base_delay_seconds * 2 ** max(0, self.failure_count - 1),
        )
        self.next_retry_at = time.monotonic() + delay

    def succeeded(self) -> None:
        self.disabled_reason = None
        self.failure_count = 0
        self.next_retry_at = 0.0

    def retry_now(self) -> None:
        self.next_retry_at = 0.0

    def status(self) -> dict[str, Any]:
        retry_in = max(0.0, self.next_retry_at - time.monotonic())
        return {
            "mode": "fallback" if self.disabled_reason else "primary",
            "failure_count": self.failure_count,
            "retry_in_seconds": round(retry_in, 1),
            **(
                {"error": self.disabled_reason}
                if self.disabled_reason is not None
                else {}
            ),
        }


@dataclass(slots=True)
class ResilientMaskRefiner:
    """Use the offline refiner after the first AI load or inference failure."""

    primary: MaskRefiner
    fallback: MaskRefiner = field(default_factory=MorphologyMaskRefiner)
    retry_state: ProviderRetryState = field(default_factory=ProviderRetryState)

    @property
    def disabled_reason(self) -> str | None:
        return self.retry_state.disabled_reason

    @property
    def name(self) -> str:
        return self.fallback.name if self.disabled_reason else self.primary.name

    @property
    def model(self) -> str | None:
        return getattr(self.primary, "model", None)

    def refine(self, image: np.ndarray, rough_mask: np.ndarray) -> np.ndarray:
        if self.retry_state.can_attempt():
            try:
                result = self.primary.refine(image, rough_mask)
                self.retry_state.succeeded()
                return result
            except Exception as error:
                self.retry_state.failed(error)
        return self.fallback.refine(image, rough_mask)

    def retry_now(self) -> None:
        self.retry_state.retry_now()

    def status(self) -> dict[str, Any]:
        return self.retry_state.status()


@dataclass(slots=True)
class FlatDepthEstimator:
    value: float = 0.5
    name: str = "flat-depth-v1"

    def estimate(self, image: np.ndarray, mask: np.ndarray) -> np.ndarray:
        del image
        return np.full(mask.shape, np.clip(self.value, 0.0, 1.0), dtype=np.float32)


@dataclass(slots=True)
class ImageAwareDepthEstimator:
    """Deterministic image-space depth proxy used until an AI provider is selected."""

    blur_radius: float = 7.0
    name: str = "image-depth-v1"

    def estimate(self, image: np.ndarray, mask: np.ndarray) -> np.ndarray:
        gray = np.asarray(
            Image.fromarray(image, mode="RGB")
            .convert("L")
            .filter(ImageFilter.GaussianBlur(radius=self.blur_radius)),
            dtype=np.float32,
        ) / 255.0
        # Darker regions usually tolerate a little more displacement; the soft
        # mask term reduces movement close to selection boundaries.
        depth = (0.3 + (1.0 - gray) * 0.45) * (0.65 + mask * 0.35)
        return np.clip(depth, 0.0, 1.0).astype(np.float32)


@dataclass(slots=True)
class TransformersDepthEstimator:
    """Optional monocular depth proposal compatible with Depth Anything models."""

    model: str = "LiheYoung/depth-anything-small-hf"
    device: int = -1
    name: str = "depth-anything-proposal"
    _pipeline: Any = field(default=None, init=False, repr=False)

    def _load(self):
        if self._pipeline is None:
            try:
                from transformers import pipeline
            except (ImportError, OSError) as error:
                raise RuntimeError(
                    "AI preparation requires PyTorch and Transformers. "
                    "Install the optional packages described in "
                    "effect_engine/README.md."
                ) from error

            try:
                self._pipeline = pipeline(
                    task="depth-estimation",
                    model=self.model,
                    device=self.device,
                )
            except (ImportError, OSError) as error:
                raise RuntimeError(
                    f"Could not load depth model {self.model!r}: {error}"
                ) from error
        return self._pipeline

    def estimate(self, image: np.ndarray, mask: np.ndarray) -> np.ndarray:
        output = self._load()(Image.fromarray(image, mode="RGB"))
        if not isinstance(output, Mapping):
            raise ValueError("Depth pipeline returned no mapping")
        raw = output.get("predicted_depth", output.get("depth"))
        depth = _pipeline_array(raw, (image.shape[1], image.shape[0]))
        selected = depth[mask > 0.1]
        if selected.size:
            low, high = np.percentile(selected, (2, 98))
        else:
            low, high = float(depth.min()), float(depth.max())
        if high - low > 1e-6:
            depth = (depth - low) / (high - low)
        else:
            depth = np.full_like(depth, 0.5)
        return np.clip(depth, 0.0, 1.0).astype(np.float32)


@dataclass(slots=True)
class ResilientDepthEstimator:
    """Use deterministic image depth after the first AI provider failure."""

    primary: DepthEstimator
    fallback: DepthEstimator = field(default_factory=ImageAwareDepthEstimator)
    retry_state: ProviderRetryState = field(default_factory=ProviderRetryState)

    @property
    def disabled_reason(self) -> str | None:
        return self.retry_state.disabled_reason

    @property
    def name(self) -> str:
        return self.fallback.name if self.disabled_reason else self.primary.name

    @property
    def model(self) -> str | None:
        return getattr(self.primary, "model", None)

    def estimate(self, image: np.ndarray, mask: np.ndarray) -> np.ndarray:
        if self.retry_state.can_attempt():
            try:
                result = self.primary.estimate(image, mask)
                self.retry_state.succeeded()
                return result
            except Exception as error:
                self.retry_state.failed(error)
        return self.fallback.estimate(image, mask)

    def retry_now(self) -> None:
        self.retry_state.retry_now()

    def status(self) -> dict[str, Any]:
        return self.retry_state.status()


def _blur_float_map(value: np.ndarray, radius: float) -> np.ndarray:
    source = np.asarray(value, dtype=np.float32)
    minimum = float(np.nanmin(source))
    maximum = float(np.nanmax(source))
    span = maximum - minimum
    if not np.isfinite(span) or span <= 1e-8:
        return np.full_like(source, minimum, dtype=np.float32)
    normalized = np.clip((source - minimum) / span, 0.0, 1.0)
    blurred = np.asarray(
        Image.fromarray(np.rint(normalized * 255.0).astype(np.uint8), mode="L").filter(
            ImageFilter.GaussianBlur(radius=max(0.0, float(radius)))
        ),
        dtype=np.float32,
    )
    return blurred * (span / 255.0) + minimum


def _axis_gradient(value: np.ndarray, axis: int) -> np.ndarray:
    if value.shape[axis] <= 1:
        return np.zeros_like(value, dtype=np.float32)
    return np.gradient(value, axis=axis).astype(np.float32)


@dataclass(slots=True)
class DirectionalFlowEstimator:
    variation: float = 0.28
    name: str = "directional-flow-v3"

    @staticmethod
    def _principal_direction(mask: np.ndarray) -> tuple[float, float]:
        ys, xs = np.nonzero(mask > 0.1)
        if len(xs) < 2:
            return 1.0, 0.0
        points = np.column_stack((xs, ys)).astype(np.float64)
        points -= points.mean(axis=0, keepdims=True)
        covariance = np.cov(points, rowvar=False)
        eigenvalues, eigenvectors = np.linalg.eigh(covariance)
        vector = eigenvectors[:, int(np.argmax(eigenvalues))]
        if vector[0] < 0 or (abs(vector[0]) < 1e-8 and vector[1] < 0):
            vector *= -1.0
        return float(vector[0]), float(vector[1])

    def estimate(
        self,
        image: np.ndarray,
        mask: np.ndarray,
        direction: tuple[float, float] | None = None,
        guides: list[dict[str, Any]] | None = None,
    ) -> np.ndarray:
        dx, dy = direction or self._principal_direction(mask)
        length = float(np.hypot(dx, dy))
        if length < 1e-8:
            dx, dy, length = 1.0, 0.0, 1.0
        dx, dy = dx / length, dy / length
        height, width = mask.shape
        y, x = np.mgrid[0:height, 0:width].astype(np.float32)
        direction_x = np.full(mask.shape, dx * 0.35, dtype=np.float32)
        direction_y = np.full(mask.shape, dy * 0.35, dtype=np.float32)
        total_weight = np.full(mask.shape, 0.35, dtype=np.float32)
        influence_radius = max(24.0, min(width, height) * 0.18)
        for guide in guides or []:
            try:
                start = np.asarray(guide["start"][:2], dtype=np.float32)
                end = np.asarray(guide["end"][:2], dtype=np.float32)
                delta = end - start
                control1 = np.asarray(
                    guide.get("control1", start + delta / 3.0)[:2],
                    dtype=np.float32,
                )
                control2 = np.asarray(
                    guide.get("control2", start + delta * 2.0 / 3.0)[:2],
                    dtype=np.float32,
                )
            except (KeyError, TypeError, ValueError, IndexError):
                continue
            if not all(
                np.isfinite(point).all()
                for point in (start, control1, control2, end)
            ):
                continue
            if float(np.linalg.norm(end - start)) < 1e-6:
                continue

            # A guide has no useful influence several radii away.  Restricting
            # the distance search to its bounding box avoids three full-frame
            # allocations and twelve full-frame distance calculations per
            # curve (particularly expensive for 4K sources).
            guide_points = np.stack((start, control1, control2, end))
            margin = influence_radius * 3.0
            x0 = max(0, int(np.floor(float(guide_points[:, 0].min()) - margin)))
            x1 = min(width, int(np.ceil(float(guide_points[:, 0].max()) + margin)) + 1)
            y0 = max(0, int(np.floor(float(guide_points[:, 1].min()) - margin)))
            y1 = min(height, int(np.ceil(float(guide_points[:, 1].max()) + margin)) + 1)
            if x0 >= x1 or y0 >= y1:
                continue
            region_x = x[y0:y1, x0:x1]
            region_y = y[y0:y1, x0:x1]
            region_shape = region_x.shape
            nearest_distance = np.full(region_shape, np.inf, dtype=np.float32)
            nearest_dx = np.zeros(region_shape, dtype=np.float32)
            nearest_dy = np.zeros(region_shape, dtype=np.float32)
            for curve_t in np.linspace(0.0, 1.0, 12, dtype=np.float32):
                inverse = np.float32(1.0) - curve_t
                point = (
                    inverse**3 * start
                    + 3.0 * inverse**2 * curve_t * control1
                    + 3.0 * inverse * curve_t**2 * control2
                    + curve_t**3 * end
                )
                tangent = (
                    3.0 * inverse**2 * (control1 - start)
                    + 6.0 * inverse * curve_t * (control2 - control1)
                    + 3.0 * curve_t**2 * (end - control2)
                )
                tangent_length = float(np.linalg.norm(tangent))
                if tangent_length < 1e-6:
                    continue
                tangent /= tangent_length
                distance_sq = (
                    (region_x - point[0]) ** 2 + (region_y - point[1]) ** 2
                )
                closer = distance_sq < nearest_distance
                nearest_distance = np.where(
                    closer, distance_sq, nearest_distance
                )
                nearest_dx = np.where(closer, tangent[0], nearest_dx)
                nearest_dy = np.where(closer, tangent[1], nearest_dy)

            distance_sq = nearest_distance
            normalized_distance = np.sqrt(distance_sq) / influence_radius
            weight = 1.0 / (1.0 + normalized_distance**2)
            # Smoothly reach zero at the ROI edge to avoid a visible boundary.
            falloff = np.clip(1.0 - normalized_distance / 3.0, 0.0, 1.0)
            weight *= falloff * falloff
            direction_x[y0:y1, x0:x1] += weight * nearest_dx
            direction_y[y0:y1, x0:x1] += weight * nearest_dy
            total_weight[y0:y1, x0:x1] += weight
        direction_x /= total_weight
        direction_y /= total_weight
        direction_length = np.maximum(
            np.hypot(direction_x, direction_y), 1e-6
        )
        direction_x /= direction_length
        direction_y /= direction_length

        # Diffuse sparse curve guidance through the selected material while
        # retaining stronger user-authored directions close to each curve.
        support = np.maximum(_blur_float_map(mask, 3.5), 1e-4)
        smooth_x = _blur_float_map(direction_x * mask, 3.5) / support
        smooth_y = _blur_float_map(direction_y * mask, 3.5) / support
        guide_confidence = np.clip((total_weight - 0.35) / 1.2, 0.0, 1.0)
        smooth_amount = (0.46 - guide_confidence * 0.28) * np.clip(mask, 0.0, 1.0)
        direction_x = direction_x * (1.0 - smooth_amount) + smooth_x * smooth_amount
        direction_y = direction_y * (1.0 - smooth_amount) + smooth_y * smooth_amount

        gray = np.asarray(
            Image.fromarray(image, mode="RGB")
            .convert("L")
            .filter(ImageFilter.GaussianBlur(radius=3.0)),
            dtype=np.float32,
        ) / 255.0
        grad_y = _axis_gradient(gray, 0)
        grad_x = _axis_gradient(gray, 1)
        edge_strength = np.hypot(grad_x, grad_y)
        selected_edges = edge_strength[mask > 0.1]
        edge_scale = (
            float(np.percentile(selected_edges, 90))
            if selected_edges.size
            else 0.0
        )
        if edge_scale > 1e-6:
            edge_weight = np.clip(edge_strength / edge_scale, 0.0, 1.0) * mask
            normal_x = grad_x / np.maximum(edge_strength, 1e-6)
            normal_y = grad_y / np.maximum(edge_strength, 1e-6)
            normal_component = direction_x * normal_x + direction_y * normal_y
            tangent_x = direction_x - normal_component * normal_x
            tangent_y = direction_y - normal_component * normal_y
            tangent_length = np.maximum(np.hypot(tangent_x, tangent_y), 1e-6)
            tangent_x /= tangent_length
            tangent_y /= tangent_length
            # Keep obstacle avoidance subordinate to the authored/global
            # direction.  A strong projection here can rotate an entire
            # vertical river because of texture edges in the source artwork.
            avoid_amount = edge_weight * 0.18
            direction_x = direction_x * (1.0 - avoid_amount) + tangent_x * avoid_amount
            direction_y = direction_y * (1.0 - avoid_amount) + tangent_y * avoid_amount

        # One inexpensive pressure-projection approximation reduces local
        # sources/sinks that otherwise stretch the animated texture.
        divergence = _axis_gradient(direction_x, 1) + _axis_gradient(direction_y, 0)
        pressure = _blur_float_map(divergence * mask, 4.0)
        direction_x -= _axis_gradient(pressure, 1) * mask * 0.32
        direction_y -= _axis_gradient(pressure, 0) * mask * 0.32
        direction_length = np.maximum(np.hypot(direction_x, direction_y), 1e-6)
        direction_x /= direction_length
        direction_y /= direction_length

        along_gradient = grad_x * direction_x + grad_y * direction_y
        scale = (
            float(np.percentile(np.abs(along_gradient[mask > 0.1]), 90))
            if np.any(mask > 0.1)
            else 0.0
        )
        if scale > 1e-6:
            variation = np.clip(along_gradient / scale, -1.0, 1.0) * self.variation
        else:
            variation = np.zeros_like(mask, dtype=np.float32)
        flow = np.zeros((*mask.shape, 2), dtype=np.float32)
        flow[..., 0] = direction_x - direction_y * variation
        flow[..., 1] = direction_y + direction_x * variation
        flow_length = np.maximum(np.linalg.norm(flow, axis=-1, keepdims=True), 1e-6)
        flow /= flow_length
        if edge_scale > 1e-6:
            obstacle_factor = 1.0 - 0.45 * np.clip(
                edge_strength / edge_scale, 0.0, 1.0
            )
        else:
            obstacle_factor = np.ones_like(mask, dtype=np.float32)
        # Keep headroom for the manual "faster" brush.  A fully selected
        # interior starts around 0.7, so a 1.5x correction is visible instead
        # of being immediately clipped at the map maximum.
        speed = np.clip((0.12 + mask * 0.58) * obstacle_factor, 0.0, 1.0)
        speed[mask <= 0.01] = 0.0
        flow *= speed[..., None]
        return flow


def _automatic_material_maps(
    image: np.ndarray,
    mask: np.ndarray,
    speed: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    """Propose protected structure and foam without changing pixels outside mask."""
    mask_image = Image.fromarray(
        np.rint(mask * 255.0).astype(np.uint8), mode="L"
    )
    eroded = np.asarray(mask_image.filter(ImageFilter.MinFilter(7)), dtype=np.float32)
    eroded /= 255.0
    boundary = np.clip(mask - eroded, 0.0, 1.0)

    gray = np.asarray(
        Image.fromarray(image, mode="RGB")
        .convert("L")
        .filter(ImageFilter.GaussianBlur(radius=1.4)),
        dtype=np.float32,
    ) / 255.0
    grad_y, grad_x = np.gradient(gray)
    edges = np.hypot(grad_x, grad_y)
    selected = edges[mask > 0.1]
    edge_scale = float(np.percentile(selected, 92)) if selected.size else 0.0
    if edge_scale > 1e-6:
        edges = np.clip(edges / edge_scale, 0.0, 1.0)
    else:
        edges = np.zeros_like(mask, dtype=np.float32)

    obstacles = np.clip(boundary * 0.9 + edges * mask * 0.18, 0.0, 1.0)
    foam = np.clip(
        (boundary * 0.18 + edges * mask * 0.28) * speed,
        0.0,
        1.0,
    )
    return obstacles.astype(np.float32), foam.astype(np.float32)


def _apply_radial_zones(
    base: np.ndarray,
    zones: list[Mapping[str, Any]],
    *,
    multiply: bool,
) -> np.ndarray:
    result = np.asarray(base, dtype=np.float32).copy()
    for zone in zones:
        region = _radial_zone_region(zone, result.shape)
        if region is None:
            continue
        y_slice, x_slice, influence = region
        try:
            value = float(zone.get("value", 1.0))
        except (TypeError, ValueError):
            continue
        target = result[y_slice, x_slice]
        if multiply:
            target *= 1.0 + (value - 1.0) * influence
        else:
            np.maximum(
                target,
                np.clip(value, 0.0, 1.0) * influence,
                out=target,
            )
    return np.clip(result, 0.0, 1.0).astype(np.float32)


def _erase_radial_zones(
    base: np.ndarray,
    zones: list[Mapping[str, Any]],
) -> np.ndarray:
    keep = np.ones_like(base, dtype=np.float32)
    erased = _apply_radial_zones(
        np.zeros_like(base, dtype=np.float32),
        zones,
        multiply=False,
    )
    keep -= erased
    return np.clip(base * keep, 0.0, 1.0).astype(np.float32)


def _blend_radial_zones(
    base: np.ndarray,
    zones: list[Mapping[str, Any]],
) -> np.ndarray:
    result = np.asarray(base, dtype=np.float32).copy()
    for zone in zones:
        region = _radial_zone_region(zone, result.shape)
        if region is None:
            continue
        y_slice, x_slice, influence = region
        try:
            value = np.clip(float(zone.get("value", 0.5)), 0.0, 1.0)
        except (TypeError, ValueError):
            continue
        target = result[y_slice, x_slice]
        target *= 1.0 - influence
        target += value * influence
    return np.clip(result, 0.0, 1.0).astype(np.float32)


def _radial_zone_region(
    zone: Mapping[str, Any],
    shape: tuple[int, int],
) -> tuple[slice, slice, np.ndarray] | None:
    """Return a clipped ROI and smooth radial influence for one brush zone."""
    try:
        center_x, center_y = map(float, zone["center"][:2])
        radius = max(1.0, float(zone["radius"]))
    except (KeyError, TypeError, ValueError, IndexError):
        return None
    if not np.isfinite((center_x, center_y, radius)).all():
        return None
    height, width = shape
    x0 = max(0, int(np.floor(center_x - radius)))
    x1 = min(width, int(np.ceil(center_x + radius)) + 1)
    y0 = max(0, int(np.floor(center_y - radius)))
    y1 = min(height, int(np.ceil(center_y + radius)) + 1)
    if x0 >= x1 or y0 >= y1:
        return None
    y, x = np.mgrid[y0:y1, x0:x1].astype(np.float32)
    distance = np.hypot(x - center_x, y - center_y) / radius
    influence = np.clip(1.0 - distance, 0.0, 1.0)
    influence *= influence * (3.0 - 2.0 * influence)
    return slice(y0, y1), slice(x0, x1), influence


@dataclass(slots=True)
class NoTextureGenerator:
    name: str = "none"

    def generate(
        self,
        image: np.ndarray,
        mask: np.ndarray,
        effect_type: str,
        seed: int,
        style: StyleProfile,
    ) -> dict[str, str]:
        del image, mask, effect_type, seed, style
        return {}


@dataclass(slots=True)
class StyleAnalyzer:
    palette_size: int = 5
    name: str = "statistics-v1"

    def analyze(self, image: np.ndarray, mask: np.ndarray) -> StyleProfile:
        selected = image[mask > 0.1]
        if selected.size == 0:
            selected = image.reshape(-1, 3)
        if len(selected) > 50_000:
            indices = np.linspace(0, len(selected) - 1, 50_000, dtype=np.int64)
            selected = selected[indices]

        palette_image = Image.fromarray(selected.reshape((-1, 1, 3)).astype(np.uint8), mode="RGB")
        quantized = palette_image.quantize(colors=max(1, self.palette_size), method=Image.Quantize.MEDIANCUT)
        colors = quantized.getpalette() or []
        counts = quantized.getcolors() or []
        counts.sort(reverse=True)
        palette = []
        for _, index in counts[: self.palette_size]:
            offset = index * 3
            if offset + 2 < len(colors):
                palette.append("#{:02x}{:02x}{:02x}".format(*colors[offset : offset + 3]))

        rgb = selected.astype(np.float32)
        luminance = rgb @ np.array([0.2126, 0.7152, 0.0722], dtype=np.float32)
        brightness = float(np.clip(luminance.mean() / 255.0, 0.0, 1.0))
        contrast = float(np.clip(luminance.std() / 80.0, 0.0, 1.0))

        gray = np.asarray(Image.fromarray(image, mode="RGB").convert("L"), dtype=np.float32)
        grad_x = np.abs(np.diff(gray, axis=1, prepend=gray[:, :1]))
        grad_y = np.abs(np.diff(gray, axis=0, prepend=gray[:1, :]))
        selected_gradient = (grad_x + grad_y)[mask > 0.1]
        mean_gradient = float(selected_gradient.mean()) if selected_gradient.size else 0.0
        edge_softness = float(1.0 - np.clip(mean_gradient / 64.0, 0.0, 1.0))

        blurred = np.asarray(
            Image.fromarray(gray.astype(np.uint8), mode="L").filter(ImageFilter.GaussianBlur(radius=1.0)),
            dtype=np.float32,
        )
        residual = np.abs(gray - blurred)[mask > 0.1]
        grain = float(np.clip((residual.mean() if residual.size else 0.0) / 24.0, 0.0, 1.0))

        return StyleProfile(
            palette=tuple(palette),
            brightness=brightness,
            contrast=contrast,
            edge_softness=edge_softness,
            grain=grain,
        )


@dataclass(slots=True)
class PreparationPipeline:
    """Prepare stable assets; AI-backed providers can replace any default stage."""

    mask_refiner: MaskRefiner = field(default_factory=MorphologyMaskRefiner)
    depth_estimator: DepthEstimator = field(default_factory=ImageAwareDepthEstimator)
    flow_estimator: FlowEstimator = field(default_factory=DirectionalFlowEstimator)
    texture_generator: TextureGenerator = field(default_factory=NoTextureGenerator)
    style_analyzer: StyleAnalyzer = field(default_factory=StyleAnalyzer)
    _force_refresh: bool = field(default=False, init=False, repr=False)

    def cache_signature(self) -> dict[str, Any]:
        def provider_identity(provider: object) -> dict[str, Any]:
            primary = getattr(provider, "primary", provider)
            return {
                "provider": f"{type(provider).__module__}.{type(provider).__name__}",
                "primary": f"{type(primary).__module__}.{type(primary).__name__}",
                "name": str(getattr(primary, "name", getattr(provider, "name", ""))),
                **(
                    {"model": str(model)}
                    if (model := getattr(primary, "model", None))
                    else {}
                ),
                **(
                    {"device": int(device)}
                    if (device := getattr(primary, "device", None)) is not None
                    else {}
                ),
            }

        return {
            "mask": provider_identity(self.mask_refiner),
            "depth": provider_identity(self.depth_estimator),
            "flow": provider_identity(self.flow_estimator),
            "texture": provider_identity(self.texture_generator),
            "style": provider_identity(self.style_analyzer),
        }

    def cache_read_allowed(self) -> bool:
        if self._force_refresh:
            return False
        for provider in (self.mask_refiner, self.depth_estimator):
            retry_state = getattr(provider, "retry_state", None)
            if (
                retry_state is not None
                and retry_state.disabled_reason is not None
                and retry_state.can_attempt()
            ):
                return False
        return True

    def retry_failed_providers(self) -> dict[str, dict[str, Any]]:
        self._force_refresh = True
        for provider in (self.mask_refiner, self.depth_estimator):
            retry = getattr(provider, "retry_now", None)
            if callable(retry):
                retry()
        return self.provider_states()

    def provider_states(self) -> dict[str, dict[str, Any]]:
        states = {}
        for key, provider in (
            ("mask", self.mask_refiner),
            ("depth", self.depth_estimator),
        ):
            status = getattr(provider, "status", None)
            states[key] = (
                dict(status())
                if callable(status)
                else {
                    "mode": "deterministic",
                    "failure_count": 0,
                    "retry_in_seconds": 0.0,
                }
            )
        return states

    def prepare(
        self,
        image: Image.Image | np.ndarray,
        rough_mask: Image.Image | np.ndarray,
        *,
        effect_type: str,
        seed: int,
        direction: tuple[float, float] | None = None,
        guides: list[dict[str, Any]] | None = None,
        manual_overrides: Mapping[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> EffectAssets:
        self._force_refresh = False
        rgb = _rgb_array(image)
        size = rgb.shape[1], rgb.shape[0]
        rough = _mask_array(rough_mask, size)
        mask = self.mask_refiner.refine(rgb, rough)
        overrides = manual_overrides or {}
        mask = _apply_radial_zones(
            mask,
            list(overrides.get("mask_add_zones") or []),
            multiply=False,
        )
        mask = _erase_radial_zones(
            mask,
            list(overrides.get("mask_remove_zones") or []),
        )
        depth = self.depth_estimator.estimate(rgb, mask)
        depth = _blend_radial_zones(
            depth,
            list(overrides.get("depth_zones") or []),
        )
        flow_kwargs: dict[str, Any] = {"direction": direction}
        if guides:
            flow_kwargs["guides"] = guides
        flow = self.flow_estimator.estimate(rgb, mask, **flow_kwargs)
        speed = np.clip(np.linalg.norm(flow, axis=-1), 0.0, 1.0)
        obstacles, foam = _automatic_material_maps(rgb, mask, speed)
        speed = _apply_radial_zones(
            speed,
            list(overrides.get("speed_zones") or []),
            multiply=True,
        )
        obstacles = _apply_radial_zones(
            obstacles,
            list(overrides.get("obstacle_zones") or []),
            multiply=False,
        )
        foam = _apply_radial_zones(
            foam,
            list(overrides.get("foam_zones") or []),
            multiply=False,
        )
        speed *= np.clip(1.0 - obstacles, 0.0, 1.0)
        speed *= mask
        style = self.style_analyzer.analyze(rgb, mask)
        textures = self.texture_generator.generate(rgb, mask, effect_type, int(seed), style)

        preparation_metadata = {
            "providers": {
                "mask": self.mask_refiner.name,
                "depth": self.depth_estimator.name,
                "flow": self.flow_estimator.name,
                "textures": self.texture_generator.name,
                "style": "statistics-v1",
            },
            "provider_models": {
                key: str(model)
                for key, provider in (
                    ("mask", self.mask_refiner),
                    ("depth", self.depth_estimator),
                )
                if (model := getattr(provider, "model", None))
            },
        }
        provider_warnings = {
            key: str(reason)
            for key, provider in (
                ("mask", self.mask_refiner),
                ("depth", self.depth_estimator),
            )
            if (reason := getattr(provider, "disabled_reason", None))
        }
        if provider_warnings:
            preparation_metadata["provider_warnings"] = provider_warnings
        preparation_metadata["provider_states"] = self.provider_states()
        preparation_metadata.update(metadata or {})
        if direction is not None:
            preparation_metadata["direction"] = [float(direction[0]), float(direction[1])]
        if guides:
            preparation_metadata["flow_guides"] = guides
        preparation_metadata["asset_layers"] = {
            "proposal": ["mask", "depth", "flow", "speed", "obstacles", "foam"],
            "manual_overrides": {
                key: len(list(overrides.get(key) or []))
                for key in (
                    "speed_zones",
                    "obstacle_zones",
                    "foam_zones",
                    "mask_add_zones",
                    "mask_remove_zones",
                    "depth_zones",
                )
            },
        }

        return EffectAssets(
            effect_type=effect_type,
            seed=int(seed),
            mask=mask,
            depth=depth,
            flow=flow,
            speed=speed,
            obstacles=obstacles,
            foam=foam,
            style=style,
            textures=textures,
            metadata=preparation_metadata,
        )


_AI_PIPELINE_CACHE: dict[tuple[str, str, int], PreparationPipeline] = {}


def create_preparation_pipeline(use_ai: bool | None = None) -> PreparationPipeline:
    """Create optional AI proposal providers while preserving an offline fallback."""
    if use_ai is None:
        use_ai = os.environ.get("AI_EDITOR_AI_PREPARATION", "0").lower() in {
            "1",
            "true",
            "yes",
        }
    if not use_ai:
        return PreparationPipeline()
    try:
        device = int(os.environ.get("AI_EDITOR_AI_DEVICE", "-1"))
    except ValueError:
        device = -1
    mask_model = os.environ.get(
        "AI_EDITOR_MASK_MODEL", "facebook/sam-vit-base"
    )
    depth_model = os.environ.get(
        "AI_EDITOR_DEPTH_MODEL", "LiheYoung/depth-anything-small-hf"
    )
    cache_key = (mask_model, depth_model, device)
    if cache_key in _AI_PIPELINE_CACHE:
        return _AI_PIPELINE_CACHE[cache_key]
    prepared = PreparationPipeline(
        mask_refiner=ResilientMaskRefiner(
            primary=TransformersMaskRefiner(
                model=mask_model,
                device=device,
            ),
        ),
        depth_estimator=ResilientDepthEstimator(
            primary=TransformersDepthEstimator(
                model=depth_model,
                device=device,
            ),
        ),
    )
    _AI_PIPELINE_CACHE[cache_key] = prepared
    return prepared
