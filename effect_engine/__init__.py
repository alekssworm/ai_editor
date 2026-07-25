"""Hybrid AI-preparation and deterministic animation engine."""

from .compositor import EffectApplication, EffectCompositor
from .context import EffectContext
from .layers import EffectFrame, EffectLayer, LayeredEffect
from .models import EffectAssets, StyleProfile
from .parameter_schema import (
    EffectParameterSchema,
    ParameterDefinition,
    ParameterSchemaRegistry,
    default_parameter_schema_registry,
)
from .plugins import (
    EffectPluginManifest,
    EffectPluginRegistry,
    default_effect_plugin_registry,
)
from .preparation import (
    PreparationPipeline,
    ResilientDepthEstimator,
    ResilientMaskRefiner,
    TransformersDepthEstimator,
    TransformersMaskRefiner,
    create_preparation_pipeline,
)
from .preset_registry import EffectPreset, PresetRegistry, default_preset_registry
from .quality import EffectQualityReport, analyze_effect_quality
from .region import EffectRegion, effect_region
from .renderer import DeterministicEffectEngine
from .session import RenderSession
from .storage import EffectAssetStore
from .temporal import TemporalSampling

__all__ = [
    "EffectApplication",
    "EffectCompositor",
    "EffectContext",
    "EffectFrame",
    "EffectLayer",
    "EffectParameterSchema",
    "EffectPluginManifest",
    "EffectPluginRegistry",
    "LayeredEffect",
    "default_effect_plugin_registry",
    "ParameterDefinition",
    "ParameterSchemaRegistry",
    "DeterministicEffectEngine",
    "EffectAssets",
    "EffectAssetStore",
    "EffectPreset",
    "EffectQualityReport",
    "EffectRegion",
    "PreparationPipeline",
    "ResilientDepthEstimator",
    "ResilientMaskRefiner",
    "RenderSession",
    "PresetRegistry",
    "StyleProfile",
    "TransformersDepthEstimator",
    "TransformersMaskRefiner",
    "TemporalSampling",
    "analyze_effect_quality",
    "effect_region",
    "create_preparation_pipeline",
    "default_parameter_schema_registry",
    "default_preset_registry",
]
