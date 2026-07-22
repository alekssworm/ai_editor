# Effect engine foundation

The pipeline deliberately separates the potentially non-deterministic preparation stage from frame rendering:

1. `PreparationPipeline` turns an image and rough mask into versioned `EffectAssets`.
2. `EffectAssetStore` saves mask, depth, direction, speed, obstacle and foam maps,
   plus the style profile, textures and seed.
3. `DeterministicEffectEngine` renders every frame from the saved assets and normalized time `t`.

The default preparation providers are lightweight deterministic fallbacks. SAM/Depth Anything or a texture-generation service can later implement the same provider protocols without changing the renderer.

Prepare a water layer from the current `shapes.json` format:

```powershell
python -m effect_engine prepare --project path\to\shapes.json --shape-id 1 --preset river --direction 1,0 --seed 42
```

Render a three-second loop:

```powershell
python -m effect_engine render --project path\to\shapes.json --assets path\to\effect_assets\shape_1 --preset river --output result.mp4 --frames 72 --fps 24
```

The renderer samples `t = frame_index / frame_count`; it never writes a duplicate final frame. Internally every animation phase uses periodic functions and normalizes `t` with modulo, so the state immediately after the last frame is exactly the state at `t=0`.

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
whole video in memory.

The current deterministic renderer supports the water tool. Fire, weather and
light cards produce a clear error until their renderers are implemented.

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

Water presets also apply effect-specific safe limits to strength and loop
cycles. Still water stays subtle, while river, fast river and waterfall allow
progressively stronger motion. These limits are shared by the local renderer
and AI post-processing so extreme settings do not turn the selected area into
rubber.

## Optional AI preparation

The `AI prep` checkbox replaces the offline mask/depth proposal providers with
Transformers pipelines. The default models follow the official Hugging Face
mask-generation and Depth Anything pipeline APIs:

- `facebook/sam-vit-base` refines the rough selected area.
- `LiheYoung/depth-anything-small-hf` proposes monocular depth.

Models are downloaded on first use and cached in the running editor process.
Leave the checkbox disabled for the lightweight deterministic preparation path.
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

The Preview dialog can display `Mask`, `Depth`, `Flow`, `Speed`, `Obstacles`
and `Foam` before export. Full-resolution export reuses the prepared assets and
does not run the AI models a second time.
