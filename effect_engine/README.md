# Effect engine foundation

The pipeline deliberately separates the potentially non-deterministic preparation stage from frame rendering:

1. `PreparationPipeline` turns an image and rough mask into versioned `EffectAssets`.
2. `EffectAssetStore` saves mask, depth, direction, speed, obstacle and foam maps,
   plus the style profile, textures and seed.
3. `DeterministicEffectEngine` renders every frame from the saved assets and normalized time `t`.

The default preparation providers are lightweight deterministic fallbacks. SAM/Depth Anything or a texture-generation service can later implement the same provider protocols without changing the renderer.

Each rendered frame now receives one immutable `EffectContext` containing the
normalized loop time, seed, prepared maps and resolved numeric parameters.
Effects are assembled from ordered layers instead of one large render method.
Water uses `waves`, `deformation`, `highlights` and `foam`; rain uses `streaks`
and `mist`; fire uses `field`, `distortion`, `flames`, `glow` and `embers`.

`EffectCompositor` applies multiple prepared effects to the same image in a
stable order. It keeps intermediate layers in floating point and converts to
8-bit RGB only once after the final effect, avoiding accumulated rounding loss.
Blending is performed in linear light instead of display-encoded sRGB, so
highlights, mist and transparent layers no longer become artificially dark.
The engine exposes it through `render_composite_frame` and
`render_composite_frames`:

```python
from effect_engine import EffectApplication, DeterministicEffectEngine

applications = [
    EffectApplication(water_assets, {"strength": 4.0}),
    EffectApplication(rain_assets, {"density": 0.6}),
]
frame = DeterministicEffectEngine().render_composite_frame(
    image, applications, t=0.25
)
```

`RenderSession` owns effect instances and their caches for one preview/export
job. `render_frames` and MP4 export create isolated sessions automatically;
call `engine.create_session()` when rendering a custom sequence concurrently.
Static maps use a thread-safe byte-budget LRU instead of retaining a fixed
number of full-resolution assets. The default per-renderer limit is 256 MB and
can be changed with `AI_EDITOR_EFFECT_CACHE_MB` (set it to `0` to disable the
cache).

Rendering also finds the active mask bounding box, adds a safe sampling margin
and processes only that region. Cropped assets are cached per `RenderSession`;
large background areas therefore do not allocate wave, normal or particle
fields on every frame. Set `AI_EDITOR_EFFECT_ROI=0` for diagnostics, or adjust
the default 96-pixel margin with `AI_EDITOR_EFFECT_ROI_MARGIN`.

Shared float32 spatial utilities live in `spatial.py`. Water and Fire use the
same tiled bilinear remap, periodic wave helper and non-quantizing Gaussian
approximation. This removes the previous private dependency from Fire to Water
and avoids converting editable flow maps to 8-bit data during smoothing.

Prepare a water layer from the current `shapes.json` format:

```powershell
python -m effect_engine prepare --project path\to\shapes.json --shape-id 1 --preset river --direction 1,0 --seed 42
```

Render a three-second loop:

```powershell
python -m effect_engine render --project path\to\shapes.json --assets path\to\effect_assets\shape_1 --preset river --output result.mp4 --frames 72 --fps 24 --temporal-samples 2 --shutter 0.5
```

The renderer samples `t = frame_index / frame_count`; it never writes a duplicate final frame. Internally every animation phase uses periodic functions and normalizes `t` with modulo, so the state immediately after the last frame is exactly the state at `t=0`.

MP4 export uses two deterministic temporal samples by default. Sub-frames are
sampled symmetrically within half of one frame, wrapped around the loop seam and
averaged in linear RGB. This adds motion blur to fast water, rain and embers
without dark sRGB blending or a discontinuity at `t=0`. Use
`--temporal-samples 1 --shutter 0` for the fastest sharp export.

## Presets

Renderer defaults are stored as versioned JSON files under
`effect_engine/presets/<effect_type>`. List installed presets with:

```powershell
python -m effect_engine presets --effect water
```

Each preset defines a stable `id`, effect type, editor key and numeric renderer
parameters. The editor saves `preset_id` in its shape card, and prepared assets
copy both `preset_id` and the resolved renderer parameters into `manifest.json`.
Old projects without `preset_id` remain compatible: keys such as `main_river`
are registered as aliases. Parameter precedence is preset, then card settings,
then explicit CLI overrides.

Water preset JSON files may also define a `controls` array. A new preset with a
unique `editor_key` is added to the water panel automatically; no generated Qt
file needs to be edited. `fast_river.json` is included as an example of a second
motion preset that uses the same water renderer.

## Editor preview

Save or open a project, select one shape with a water card, then press the main
window's `preview` button. Preparation runs outside the UI thread and writes the
full-resolution maps to `effect_assets/shape_<id>`. The preview dialog renders a
smaller 640-pixel copy of those maps as an 18-frame loop, so preview speed does
not reduce the quality of assets kept for export. Press `Export MP4 (24 fps)`
inside the preview window for a full-resolution 72-frame H.264 loop. The export
streams frames to an atomic temporary file at CRF 18 instead of keeping the
whole video in memory. `Before` temporarily shows the unmodified preview source;
the button changes to `After` to return to the animated result. The adjacent
Fast/Balanced/High selector uses 1, 2 or 4 temporal samples per exported frame.

The deterministic renderer supports Water, Weather → Rain and Fire. Fire
includes Campfire, Torch, Candle and Lava presets. Fog, wind, smoke and light
cards remain disabled until their renderers are implemented.

### Parameter schemas

AI Panel controls are generated from JSON files under `effect_engine/schemas`.
Each definition provides a stable parameter id, label, value type, default,
limits, step and optional suffix/options. Preset `controls` arrays choose which
schema fields are shown. Adding a parameter or a rain/water preset therefore no
longer requires editing the panel's Python layout code. Older qualitative water
values such as `weak`, `default` and `strong` remain compatible.

Rain is the second plugin and validates the shared architecture: its preset is
stored under `effect_engine/presets/rain`, its controls are numeric and generated
from `schemas/rain.json`, and its streak/mist layers are periodic at `t=1`.
Renderer and editor-panel registration share one manifest in `plugins.py`, so a
new effect is not registered independently in two different code paths.
Fire is the third plugin and uses the same manifest, preset and schema path
without special-casing the renderer or ShapeCard.
Rain streaks/mist and Fire flames/embers now respect the prepared obstacle map,
so protected foreground objects occlude particles instead of being painted over.

### Flow direction

Select an area and press `settings`, then drag over the area in the intended
direction of motion. The pointer trail becomes a cubic curve instead of a single
straight vector. A normal drag replaces the flow and `Shift`+drag adds up to
eight curves for bends, banks and waterfalls.

The same tool paints manual corrections with modifier-drag gestures:

- `Ctrl`: faster water (green); `Ctrl+Shift`: slower water (orange)
- `Alt`: protected/immovable structure (red); `Alt+Shift`: foam (white)
- `Ctrl+Alt`: include in AI mask (blue); `Ctrl+Alt+Shift`: exclude (purple)
- middle-button drag: deeper water (cyan); `Shift`+middle: shallower (navy)

Curves are saved under `flow_guides`; corrections are saved separately under
`effect_overrides`. Re-running preparation therefore replaces AI proposals but
reapplies the user's edits afterwards. `Esc` or a second press on `settings`
finishes editing; `Delete` clears the selected area's manual curves and maps.
`Ctrl+Z`, `Ctrl+Y` and `Ctrl+Shift+Z` undo and redo flow curves and painted map
zones for the selected area.

Water presets also apply effect-specific safe limits to strength and loop
cycles. Still water stays subtle, while river, fast river and waterfall allow
progressively stronger motion. These limits are shared by the local renderer
and AI post-processing so extreme settings do not turn the selected area into
rubber.

Prepared foam is split into anchored contact foam and a flow-guided moving
component. Two advected samples crossfade over the loop, preserving motion
direction without introducing a cut at `t=1`. Large foam regions are sampled at
an adaptive resolution before compositing to keep 4K memory and render time
bounded.

## Optional AI preparation

The `AI prep` checkbox replaces the offline mask/depth proposal providers with
Transformers pipelines. The default models follow the official Hugging Face
mask-generation and Depth Anything pipeline APIs:

- `facebook/sam-vit-base` refines the rough selected area.
- `LiheYoung/depth-anything-small-hf` proposes monocular depth.

Models are downloaded on first use and cached in the running editor process.
Leave the checkbox disabled for the lightweight deterministic preparation path.
If model loading or inference fails, preparation continues with the offline
mask/depth provider and Preview displays an `AI fallback` warning with the
original error. Failed providers use exponential retry backoff; `Retry AI`
clears the backoff and prepares the open preview again. Mask and Depth status
are shown separately in the preview.
Install `torch` for the intended CPU/CUDA environment first, then install the
client-side model API in the editor virtual environment:

```powershell
.\.venv\Scripts\python.exe -m pip install "transformers>=4.57,<5"
```

The model and device can be changed without code edits:

```powershell
$env:AI_EDITOR_MASK_MODEL = "facebook/sam-vit-base"
$env:AI_EDITOR_DEPTH_MODEL = "LiheYoung/depth-anything-small-hf"
$env:AI_EDITOR_AI_DEVICE = "0"  # CUDA device; use -1 for CPU
```

Preparation is cached on disk by a fingerprint of the source image, rough mask,
flow guides, manual corrections, seed and provider configuration. Adjusting
renderer-only strength or opacity therefore reuses Mask/Depth/Flow assets.

The Preview dialog can overlay `Mask`, `Depth`, `Flow`, color-mapped `Speed`,
`Obstacles` and `Foam` on the animated result with adjustable opacity.
Full-resolution export reuses the prepared assets and does not run the AI
models a second time.

## Automated quality checks

`analyze_effect_quality` renders a short sequence and reports determinism,
changes outside the prepared mask, loop-seam continuity, average frame time and
peak Python-managed memory:

```python
from effect_engine import analyze_effect_quality

report = analyze_effect_quality(image, assets, params=params, frame_count=12)
assert report.passed, report.to_dict()
```

Engine tests apply the same gates to the built-in effects, including Fire.
