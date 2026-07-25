from __future__ import annotations

import json
import math
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, Mapping


PRESET_SCHEMA_VERSION = 1


def _normalized(value: Any) -> str:
    return str(value or "").strip().lower()


@dataclass(frozen=True, slots=True)
class EffectPreset:
    preset_id: str
    effect_type: str
    label: str
    params: dict[str, float]
    aliases: tuple[str, ...] = ()
    controls: tuple[str, ...] = ()
    editor_key: str | None = None
    is_default: bool = False
    schema_version: int = PRESET_SCHEMA_VERSION

    @classmethod
    def from_dict(
        cls, data: Mapping[str, Any], *, source: str = "<memory>"
    ) -> "EffectPreset":
        try:
            schema_version = int(data.get("schema_version", PRESET_SCHEMA_VERSION))
        except (TypeError, ValueError) as error:
            raise ValueError(f"Invalid preset schema_version in {source}") from error
        if schema_version != PRESET_SCHEMA_VERSION:
            raise ValueError(
                f"Unsupported preset schema_version {schema_version} in {source}"
            )

        preset_id = _normalized(data.get("id"))
        effect_type = _normalized(data.get("effect_type"))
        label = str(data.get("label") or "").strip()
        if not preset_id or not effect_type or not label:
            raise ValueError(f"Preset id, effect_type and label are required in {source}")

        raw_params = data.get("params")
        if not isinstance(raw_params, Mapping) or not raw_params:
            raise ValueError(f"Preset params must be a non-empty object in {source}")
        params: dict[str, float] = {}
        for raw_name, raw_value in raw_params.items():
            name = _normalized(raw_name)
            try:
                value = float(raw_value)
            except (TypeError, ValueError) as error:
                raise ValueError(
                    f"Preset parameter '{raw_name}' is not numeric in {source}"
                ) from error
            if not name or not math.isfinite(value):
                raise ValueError(f"Invalid preset parameter '{raw_name}' in {source}")
            params[name] = value

        raw_aliases = data.get("aliases") or []
        if not isinstance(raw_aliases, list):
            raise ValueError(f"Preset aliases must be an array in {source}")
        aliases = tuple(
            alias for alias in (_normalized(value) for value in raw_aliases) if alias
        )
        raw_controls = data.get("controls") or []
        if not isinstance(raw_controls, list):
            raise ValueError(f"Preset controls must be an array in {source}")
        controls = tuple(
            str(value).strip() for value in raw_controls if str(value).strip()
        )
        editor_key = str(data.get("editor_key") or "").strip() or None
        return cls(
            preset_id=preset_id,
            effect_type=effect_type,
            label=label,
            params=params,
            aliases=aliases,
            controls=controls,
            editor_key=editor_key,
            is_default=bool(data.get("default", False)),
            schema_version=schema_version,
        )


class PresetRegistry:
    def __init__(self, presets: list[EffectPreset]) -> None:
        self._presets: dict[tuple[str, str], EffectPreset] = {}
        self._aliases: dict[tuple[str, str], str] = {}
        self._defaults: dict[str, str] = {}
        for preset in presets:
            key = preset.effect_type, preset.preset_id
            if key in self._presets:
                raise ValueError(
                    f"Duplicate preset '{preset.effect_type}/{preset.preset_id}'"
                )
            self._presets[key] = preset

            references = (
                preset.preset_id,
                f"main_{preset.preset_id}",
                *preset.aliases,
            )
            if preset.editor_key:
                references = (*references, preset.editor_key)
            for reference in references:
                alias_key = preset.effect_type, _normalized(reference)
                previous = self._aliases.get(alias_key)
                if previous is not None and previous != preset.preset_id:
                    raise ValueError(
                        f"Duplicate preset alias '{preset.effect_type}/{reference}'"
                    )
                self._aliases[alias_key] = preset.preset_id

            if preset.is_default:
                if preset.effect_type in self._defaults:
                    raise ValueError(f"Multiple default presets for '{preset.effect_type}'")
                self._defaults[preset.effect_type] = preset.preset_id

        for effect_type in {preset.effect_type for preset in presets}:
            if effect_type not in self._defaults:
                raise ValueError(
                    f"Missing default preset for '{effect_type}'"
                )

    @classmethod
    def from_directory(cls, directory: str | Path) -> "PresetRegistry":
        root = Path(directory)
        presets = []
        for path in sorted(root.rglob("*.json")):
            data = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(data, Mapping):
                raise ValueError(f"Preset root must be an object in {path}")
            presets.append(EffectPreset.from_dict(data, source=str(path)))
        if not presets:
            raise ValueError(f"No preset JSON files found in {root}")
        return cls(presets)

    def supports(self, effect_type: str) -> bool:
        return _normalized(effect_type) in self._defaults

    def resolve(self, effect_type: str, reference: str | None = None) -> EffectPreset:
        normalized_effect = _normalized(effect_type)
        normalized_reference = _normalized(reference)
        if not normalized_reference:
            try:
                normalized_reference = self._defaults[normalized_effect]
            except KeyError as error:
                raise KeyError(
                    f"No presets registered for effect '{effect_type}'"
                ) from error
        preset_id = self._aliases.get((normalized_effect, normalized_reference))
        if preset_id is None:
            raise KeyError(f"Unknown preset '{effect_type}/{reference}'")
        return self._presets[(normalized_effect, preset_id)]

    def list(self, effect_type: str | None = None) -> tuple[EffectPreset, ...]:
        normalized_effect = _normalized(effect_type)
        values = (
            preset
            for preset in self._presets.values()
            if not normalized_effect or preset.effect_type == normalized_effect
        )
        return tuple(
            sorted(values, key=lambda preset: (preset.effect_type, preset.preset_id))
        )


@lru_cache(maxsize=1)
def default_preset_registry() -> PresetRegistry:
    return PresetRegistry.from_directory(Path(__file__).with_name("presets"))


def card_preset_reference(card: Mapping[str, Any] | None) -> str | None:
    card = card or {}
    explicit = _normalized(card.get("preset_id"))
    if explicit:
        return explicit
    main = card.get("main") or {}
    if not isinstance(main, Mapping):
        return None
    return _normalized(main.get("key") or main.get("name")) or None


def resolve_card_preset(
    card: Mapping[str, Any] | None,
    effect_type: str,
    *,
    preset_id: str | None = None,
    registry: PresetRegistry | None = None,
) -> EffectPreset | None:
    selected_registry = registry or default_preset_registry()
    if not selected_registry.supports(effect_type):
        return None
    reference = preset_id or card_preset_reference(card)
    return selected_registry.resolve(effect_type, reference)


def preset_id_from_card(
    card: Mapping[str, Any] | None,
    effect_type: str | None = None,
    *,
    registry: PresetRegistry | None = None,
) -> str | None:
    resolved_effect = effect_type or str((card or {}).get("tool_type") or "")
    preset = resolve_card_preset(card, resolved_effect, registry=registry)
    return preset.preset_id if preset is not None else None
