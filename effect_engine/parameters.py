from __future__ import annotations

import math
from typing import Any, Mapping

from .parameter_schema import default_parameter_schema_registry
from .preset_registry import PresetRegistry, resolve_card_preset


_LEVELS = {
    "none": 0.0,
    "default": 1.0,
    "low": 0.65,
    "weak": 0.65,
    "normal": 1.0,
    "medium": 1.0,
    "high": 1.45,
    "strong": 1.45,
}

_OPACITY_LEVELS = {
    "none": 0.0,
    "default": 0.75,
    "low": 0.45,
    "weak": 0.45,
    "normal": 0.75,
    "medium": 0.75,
    "high": 1.0,
    "strong": 1.0,
}

_TRANSPARENCY_MULTIPLIERS = {
    "none": 1.0,
    "default": 1.0,
    "low": 0.9,
    "weak": 0.9,
    "normal": 0.7,
    "medium": 0.7,
    "high": 0.45,
    "strong": 0.45,
}

_MOTION_PROFILES = {
    "still_water": {
        "recommended_strength": 2.0,
        "max_strength": 4.0,
        "recommended_cycles": 1,
        "max_cycles": 2,
    },
    "river": {
        "recommended_strength": 4.0,
        "max_strength": 10.0,
        "recommended_cycles": 1,
        "max_cycles": 3,
    },
    "fast_river": {
        "recommended_strength": 7.0,
        "max_strength": 12.0,
        "recommended_cycles": 2,
        "max_cycles": 3,
    },
    "waterfall": {
        "recommended_strength": 8.0,
        "max_strength": 14.0,
        "recommended_cycles": 2,
        "max_cycles": 3,
    },
    "rain": {
        "recommended_strength": 4.0,
        "max_strength": 14.0,
        "recommended_cycles": 2,
        "max_cycles": 6,
    },
}


def motion_profile_from_card(
    card: Mapping[str, Any] | None,
    *,
    effect_type: str | None = None,
    preset_id: str | None = None,
    registry: PresetRegistry | None = None,
) -> dict[str, float]:
    resolved_effect = str(
        effect_type or (card or {}).get("tool_type") or "water"
    ).lower()
    preset = resolve_card_preset(
        card,
        resolved_effect,
        preset_id=preset_id,
        registry=registry,
    )
    key = preset.preset_id if preset is not None else ""
    profile = _MOTION_PROFILES.get(
        key,
        {
            "recommended_strength": 4.0,
            "max_strength": 20.0,
            "recommended_cycles": 1,
            "max_cycles": 4,
        },
    )
    return dict(profile)


def _main_params(card: Mapping[str, Any] | None) -> dict[str, Any]:
    main = (card or {}).get("main") or {}
    if not isinstance(main, Mapping):
        return {}
    params = main.get("params") or {}
    return dict(params) if isinstance(params, Mapping) else {}


def _level(value: Any, values: Mapping[str, float], default: float) -> float:
    return float(values.get(str(value or "default").strip().lower(), default))


def renderer_params_from_card(
    card: Mapping[str, Any] | None,
    *,
    effect_type: str | None = None,
    preset_id: str | None = None,
    registry: PresetRegistry | None = None,
) -> dict[str, float]:
    """Merge a reusable preset with qualitative settings from an editor card."""
    resolved_effect = str(
        effect_type or (card or {}).get("tool_type") or "water"
    ).lower()
    preset = resolve_card_preset(
        card,
        resolved_effect,
        preset_id=preset_id,
        registry=registry,
    )
    result = dict(preset.params) if preset is not None else {}
    values = _main_params(card)
    if resolved_effect == "water":
        intensity = _level(values.get("intensity"), _LEVELS, 1.0)
        power = _level(values.get("power"), _LEVELS, 1.0)
        result["strength"] = result.get("strength", 4.0) * intensity * power
        opacity_value = str(values.get("opacity") or "default").strip().lower()
        if opacity_value != "default":
            result["opacity"] = _level(opacity_value, _OPACITY_LEVELS, 0.75)
        else:
            result.setdefault("opacity", 0.75)

        transparency = str(
            values.get("transparency") or "default"
        ).strip().lower()
        result["opacity"] *= _TRANSPARENCY_MULTIPLIERS.get(
            transparency,
            1.0,
        )

        randomness = _level(values.get("randomness"), _LEVELS, 1.0)
        result["secondary_wavelength"] = result.get(
            "secondary_wavelength", 31.0
        ) / max(0.5, randomness)
        viscosity = _level(values.get("viscosity"), _LEVELS, 1.0)
        result["wavelength"] = result.get("wavelength", 56.0) * viscosity

        reflections = _level(values.get("reflections"), _LEVELS, 1.0)
        result["highlight"] = result.get("highlight", 0.18) * reflections

        grain = _level(values.get("grain"), _LEVELS, 1.0)
        result["turbulence"] = result.get("turbulence", 0.25) * grain
        result["shimmer"] = result.get("shimmer", 0.04) * grain
    else:
        schemas = default_parameter_schema_registry()
        if schemas.supports(resolved_effect):
            schema = schemas.get(resolved_effect)
            for definition in schema.parameters:
                raw = values.get(
                    definition.parameter_id,
                    values.get(definition.label),
                )
                if raw is None:
                    continue
                value = definition.coerce(raw)
                if isinstance(value, (int, float)):
                    result[definition.parameter_id] = float(value)

    motion = (card or {}).get("motion") or {}
    if isinstance(motion, Mapping):
        try:
            strength = float(motion.get("strength"))
            if math.isfinite(strength):
                result["strength"] = min(32.0, max(0.25, strength))
        except (TypeError, ValueError):
            pass
        try:
            cycles = int(motion.get("cycles"))
            result["cycles"] = float(min(8, max(1, cycles)))
        except (TypeError, ValueError):
            pass
    profile = motion_profile_from_card(
        card,
        effect_type=resolved_effect,
        preset_id=preset.preset_id if preset is not None else preset_id,
        registry=registry,
    )
    result["strength"] = min(result.get("strength", 4.0), profile["max_strength"])
    if "cycles" in result:
        result["cycles"] = float(
            min(int(result["cycles"]), int(profile["max_cycles"]))
        )
    return result
