# Effect engine foundation

The pipeline deliberately separates the potentially non-deterministic preparation stage from frame rendering:

1. `PreparationPipeline` turns an image and rough mask into versioned `EffectAssets`.
2. `EffectAssetStore` saves the mask, depth map, flow map, style profile, textures and seed.
3. `DeterministicEffectEngine` renders every frame from the saved assets and normalized time `t`.

The default preparation providers are lightweight deterministic fallbacks. SAM/Depth Anything or a texture-generation service can later implement the same provider protocols without changing the renderer.

Prepare a water layer from the current `shapes.json` format:

```powershell
python -m effect_engine prepare --project path\to\shapes.json --shape-id 1 --direction 1,0 --seed 42
```

Render a three-second loop:

```powershell
python -m effect_engine render --project path\to\shapes.json --assets path\to\effect_assets\shape_1 --output result.mp4 --frames 72 --fps 24
```

The renderer samples `t = frame_index / frame_count`; it never writes a duplicate final frame. Internally every animation phase uses periodic functions and normalizes `t` with modulo, so the state immediately after the last frame is exactly the state at `t=0`.
