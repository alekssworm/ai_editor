# Effect engine foundation

The pipeline deliberately separates the potentially non-deterministic preparation stage from frame rendering:

1. `PreparationPipeline` turns an image and rough mask into versioned `EffectAssets`.
2. `EffectAssetStore` saves the mask, depth map, flow map, style profile, textures and seed.
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
not reduce the quality of assets kept for export.

The current deterministic renderer supports the water tool. Fire, weather and
light cards produce a clear error until their renderers are implemented.

### Flow direction

Select an area and press `settings`, then drag over the area in the intended
direction of motion. The normalized vector is displayed as a cyan arrow, saved
under `flow_directions` in `shapes.json`, and used by both Preview and CLI asset
preparation. Right-click, `Esc`, or a second press on `settings` cancels editing.
