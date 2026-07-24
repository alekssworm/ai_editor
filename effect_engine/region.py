from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .models import EffectAssets


@dataclass(frozen=True, slots=True)
class EffectRegion:
    x0: int
    y0: int
    x1: int
    y1: int
    assets: EffectAssets
    borrowed_assets: bool = False

    @property
    def width(self) -> int:
        return self.x1 - self.x0

    @property
    def height(self) -> int:
        return self.y1 - self.y0

    @property
    def pixels(self) -> int:
        return self.width * self.height

    @property
    def slices(self) -> tuple[slice, slice]:
        return slice(self.y0, self.y1), slice(self.x0, self.x1)


def effect_region(
    assets: EffectAssets,
    *,
    margin: int = 96,
    threshold: float = 1e-6,
) -> EffectRegion | None:
    """Crop dense maps to the selected material plus a safe sampling margin."""
    selected = np.asarray(assets.mask) > float(threshold)
    selected_y = np.flatnonzero(np.any(selected, axis=1))
    selected_x = np.flatnonzero(np.any(selected, axis=0))
    if selected_x.size == 0 or selected_y.size == 0:
        return None
    safe_margin = max(0, int(margin))
    x0 = max(0, int(selected_x[0]) - safe_margin)
    x1 = min(assets.width, int(selected_x[-1]) + safe_margin + 1)
    y0 = max(0, int(selected_y[0]) - safe_margin)
    y1 = min(assets.height, int(selected_y[-1]) + safe_margin + 1)
    if x0 == 0 and y0 == 0 and x1 == assets.width and y1 == assets.height:
        return EffectRegion(
            x0=0,
            y0=0,
            x1=assets.width,
            y1=assets.height,
            assets=assets,
            borrowed_assets=True,
        )
    y_slice, x_slice = slice(y0, y1), slice(x0, x1)
    metadata = dict(assets.metadata)
    metadata["render_region"] = {
        "x": x0,
        "y": y0,
        "width": x1 - x0,
        "height": y1 - y0,
        "source_width": assets.width,
        "source_height": assets.height,
    }
    cropped = EffectAssets(
        effect_type=assets.effect_type,
        seed=assets.seed,
        mask=assets.mask[y_slice, x_slice],
        depth=assets.depth[y_slice, x_slice],
        flow=assets.flow[y_slice, x_slice],
        speed=assets.speed[y_slice, x_slice],
        obstacles=assets.obstacles[y_slice, x_slice],
        foam=assets.foam[y_slice, x_slice],
        style=assets.style,
        textures=dict(assets.textures),
        metadata=metadata,
        version=assets.version,
    )
    return EffectRegion(
        x0=x0,
        y0=y0,
        x1=x1,
        y1=y1,
        assets=cropped,
    )


def effect_region_nbytes(region: EffectRegion | None) -> int:
    if region is None or region.borrowed_assets:
        return 0
    assets = region.assets
    return int(
        assets.mask.nbytes
        + assets.depth.nbytes
        + assets.flow.nbytes
        + assets.speed.nbytes
        + assets.obstacles.nbytes
        + assets.foam.nbytes
    )
