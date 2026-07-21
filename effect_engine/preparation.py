from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol

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
class DirectionalFlowEstimator:
    variation: float = 0.28
    name: str = "directional-flow-v2"

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
    ) -> np.ndarray:
        dx, dy = direction or self._principal_direction(mask)
        length = float(np.hypot(dx, dy))
        if length < 1e-8:
            dx, dy, length = 1.0, 0.0, 1.0
        dx, dy = dx / length, dy / length
        gray = np.asarray(
            Image.fromarray(image, mode="RGB")
            .convert("L")
            .filter(ImageFilter.GaussianBlur(radius=3.0)),
            dtype=np.float32,
        ) / 255.0
        grad_y, grad_x = np.gradient(gray)
        along_gradient = grad_x * dx + grad_y * dy
        scale = float(np.percentile(np.abs(along_gradient[mask > 0.1]), 90)) if np.any(mask > 0.1) else 0.0
        if scale > 1e-6:
            variation = np.clip(along_gradient / scale, -1.0, 1.0) * self.variation
        else:
            variation = np.zeros_like(mask, dtype=np.float32)
        flow = np.zeros((*mask.shape, 2), dtype=np.float32)
        flow[..., 0] = float(dx) - float(dy) * variation
        flow[..., 1] = float(dy) + float(dx) * variation
        flow_length = np.maximum(np.linalg.norm(flow, axis=-1, keepdims=True), 1e-6)
        flow /= flow_length
        return flow


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

    def prepare(
        self,
        image: Image.Image | np.ndarray,
        rough_mask: Image.Image | np.ndarray,
        *,
        effect_type: str,
        seed: int,
        direction: tuple[float, float] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> EffectAssets:
        rgb = _rgb_array(image)
        size = rgb.shape[1], rgb.shape[0]
        rough = _mask_array(rough_mask, size)
        mask = self.mask_refiner.refine(rgb, rough)
        depth = self.depth_estimator.estimate(rgb, mask)
        flow = self.flow_estimator.estimate(rgb, mask, direction=direction)
        style = self.style_analyzer.analyze(rgb, mask)
        textures = self.texture_generator.generate(rgb, mask, effect_type, int(seed), style)

        preparation_metadata = {
            "providers": {
                "mask": self.mask_refiner.name,
                "depth": self.depth_estimator.name,
                "flow": self.flow_estimator.name,
                "textures": self.texture_generator.name,
                "style": "statistics-v1",
            }
        }
        preparation_metadata.update(metadata or {})
        if direction is not None:
            preparation_metadata["direction"] = [float(direction[0]), float(direction[1])]

        return EffectAssets(
            effect_type=effect_type,
            seed=int(seed),
            mask=mask,
            depth=depth,
            flow=flow,
            style=style,
            textures=textures,
            metadata=preparation_metadata,
        )
