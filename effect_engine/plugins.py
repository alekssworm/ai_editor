from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import Callable

from .effects.base import EffectRenderer
from .effects.rain import RainEffect
from .effects.water import WaterFlowEffect


@dataclass(frozen=True, slots=True)
class EffectPluginManifest:
    """Single source of truth for renderer and editor-panel registration."""

    effect_type: str
    renderer_factory: Callable[[], EffectRenderer]
    panel_id: str
    panel_container: str

    def __post_init__(self) -> None:
        for field_name in ("effect_type", "panel_id"):
            value = getattr(self, field_name)
            normalized = str(value).strip().lower()
            if not normalized:
                raise ValueError(f"{field_name} must not be empty")
            object.__setattr__(self, field_name, normalized)
        container = str(self.panel_container).strip()
        if not container:
            raise ValueError("panel_container must not be empty")
        object.__setattr__(self, "panel_container", container)

    def create_renderer(self) -> EffectRenderer:
        renderer = self.renderer_factory()
        if renderer.effect_type.lower() != self.effect_type:
            raise ValueError(
                "Plugin renderer effect_type does not match manifest: "
                f"{renderer.effect_type!r} != {self.effect_type!r}"
            )
        return renderer


class EffectPluginRegistry:
    def __init__(self, manifests: tuple[EffectPluginManifest, ...]) -> None:
        self._manifests: dict[str, EffectPluginManifest] = {}
        for manifest in manifests:
            if manifest.effect_type in self._manifests:
                raise ValueError(f"Duplicate effect plugin '{manifest.effect_type}'")
            self._manifests[manifest.effect_type] = manifest

    def get(self, effect_type: str) -> EffectPluginManifest:
        return self._manifests[effect_type.strip().lower()]

    def list(self) -> tuple[EffectPluginManifest, ...]:
        return tuple(self._manifests.values())

    def for_panel(self, panel_id: str) -> tuple[EffectPluginManifest, ...]:
        normalized = panel_id.strip().lower()
        return tuple(
            manifest
            for manifest in self._manifests.values()
            if manifest.panel_id == normalized
        )


@lru_cache(maxsize=1)
def default_effect_plugin_registry() -> EffectPluginRegistry:
    return EffectPluginRegistry(
        (
            EffectPluginManifest(
                effect_type="water",
                renderer_factory=WaterFlowEffect,
                panel_id="water",
                panel_container="splitter_347",
            ),
            EffectPluginManifest(
                effect_type="rain",
                renderer_factory=RainEffect,
                panel_id="weather",
                panel_container="splitter_323",
            ),
        )
    )
