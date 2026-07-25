from __future__ import annotations

import json
import math
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, Mapping


PARAMETER_SCHEMA_VERSION = 1


@dataclass(frozen=True, slots=True)
class ParameterDefinition:
    parameter_id: str
    label: str
    kind: str
    default: Any
    minimum: float | None = None
    maximum: float | None = None
    step: float | None = None
    suffix: str = ""
    options: tuple[str, ...] = ()
    tooltip: str = ""

    @classmethod
    def from_dict(cls, data: Mapping[str, Any], *, source: str) -> "ParameterDefinition":
        parameter_id = str(data.get("id") or "").strip()
        label = str(data.get("label") or parameter_id).strip()
        kind = str(data.get("type") or "float").strip().lower()
        if not parameter_id or not label or kind not in {"float", "int", "enum"}:
            raise ValueError(f"Invalid parameter definition in {source}")
        options = tuple(str(value) for value in data.get("options") or [])
        if kind == "enum" and not options:
            raise ValueError(f"Enum parameter {parameter_id!r} has no options in {source}")
        default = data.get("default", options[0] if options else 0)

        def optional_number(name: str) -> float | None:
            raw = data.get(name)
            if raw is None:
                return None
            try:
                value = float(raw)
            except (TypeError, ValueError) as error:
                raise ValueError(
                    f"Invalid {name} for parameter {parameter_id!r} in {source}"
                ) from error
            if not math.isfinite(value):
                raise ValueError(
                    f"Non-finite {name} for parameter {parameter_id!r} in {source}"
                )
            return value

        definition = cls(
            parameter_id=parameter_id,
            label=label,
            kind=kind,
            default=default,
            minimum=optional_number("minimum"),
            maximum=optional_number("maximum"),
            step=optional_number("step"),
            suffix=str(data.get("suffix") or ""),
            options=options,
            tooltip=str(data.get("tooltip") or ""),
        )
        definition.coerce(default)
        return definition

    def coerce(self, value: Any) -> str | int | float:
        if self.kind == "enum":
            text = str(value)
            return text if text in self.options else str(self.default)
        try:
            numeric = float(value)
        except (TypeError, ValueError):
            numeric = float(self.default)
        if not math.isfinite(numeric):
            numeric = float(self.default)
        if self.minimum is not None:
            numeric = max(self.minimum, numeric)
        if self.maximum is not None:
            numeric = min(self.maximum, numeric)
        return int(round(numeric)) if self.kind == "int" else float(numeric)


@dataclass(frozen=True, slots=True)
class EffectParameterSchema:
    effect_type: str
    parameters: tuple[ParameterDefinition, ...]
    schema_version: int = PARAMETER_SCHEMA_VERSION

    @classmethod
    def from_dict(
        cls, data: Mapping[str, Any], *, source: str = "<memory>"
    ) -> "EffectParameterSchema":
        try:
            version = int(data.get("schema_version", PARAMETER_SCHEMA_VERSION))
        except (TypeError, ValueError) as error:
            raise ValueError(f"Invalid parameter schema version in {source}") from error
        if version != PARAMETER_SCHEMA_VERSION:
            raise ValueError(f"Unsupported parameter schema version {version} in {source}")
        effect_type = str(data.get("effect_type") or "").strip().lower()
        raw_parameters = data.get("parameters")
        if not effect_type or not isinstance(raw_parameters, list):
            raise ValueError(f"Parameter schema requires effect_type and parameters in {source}")
        parameters = tuple(
            ParameterDefinition.from_dict(item, source=source)
            for item in raw_parameters
            if isinstance(item, Mapping)
        )
        if not parameters:
            raise ValueError(f"Parameter schema is empty in {source}")
        identifiers = [item.parameter_id for item in parameters]
        if len(identifiers) != len(set(identifiers)):
            raise ValueError(f"Duplicate parameter id in {source}")
        return cls(effect_type=effect_type, parameters=parameters, schema_version=version)

    def get(self, parameter_id: str) -> ParameterDefinition:
        for definition in self.parameters:
            if definition.parameter_id == parameter_id:
                return definition
        raise KeyError(f"Unknown parameter '{self.effect_type}/{parameter_id}'")

    def select(self, identifiers: tuple[str, ...] | list[str]) -> tuple[ParameterDefinition, ...]:
        return tuple(self.get(identifier) for identifier in identifiers)


class ParameterSchemaRegistry:
    def __init__(self, schemas: list[EffectParameterSchema]) -> None:
        self._schemas = {schema.effect_type: schema for schema in schemas}
        if len(self._schemas) != len(schemas):
            raise ValueError("Duplicate effect parameter schema")

    @classmethod
    def from_directory(cls, directory: str | Path) -> "ParameterSchemaRegistry":
        schemas = []
        for path in sorted(Path(directory).glob("*.json")):
            data = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(data, Mapping):
                raise ValueError(f"Parameter schema root must be an object in {path}")
            schemas.append(EffectParameterSchema.from_dict(data, source=str(path)))
        if not schemas:
            raise ValueError(f"No parameter schemas found in {directory}")
        return cls(schemas)

    def get(self, effect_type: str) -> EffectParameterSchema:
        try:
            return self._schemas[str(effect_type).strip().lower()]
        except KeyError as error:
            raise KeyError(f"No parameter schema for effect '{effect_type}'") from error

    def supports(self, effect_type: str) -> bool:
        return str(effect_type).strip().lower() in self._schemas


@lru_cache(maxsize=1)
def default_parameter_schema_registry() -> ParameterSchemaRegistry:
    return ParameterSchemaRegistry.from_directory(Path(__file__).with_name("schemas"))
