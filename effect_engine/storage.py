from __future__ import annotations

import json
import os
import uuid
from pathlib import Path

import numpy as np
from PIL import Image

from .models import EffectAssets, StyleProfile


class EffectAssetStore:
    MANIFEST_NAME = "manifest.json"

    @classmethod
    def save(cls, assets: EffectAssets, directory: str | Path) -> Path:
        assets.validate()
        target = Path(directory)
        target.mkdir(parents=True, exist_ok=True)

        token = uuid.uuid4().hex[:12]
        files = {
            "mask": f"mask-{token}.png",
            "depth": f"depth-{token}.png",
            "flow": f"flow-{token}.npz",
        }
        new_paths = [target / filename for filename in files.values()]
        manifest_path = target / cls.MANIFEST_NAME
        previous_files = []
        try:
            previous = json.loads(manifest_path.read_text(encoding="utf-8"))
            previous_files = list((previous.get("files") or {}).values())
        except (OSError, ValueError, AttributeError):
            pass

        mask_u8 = np.rint(assets.mask * 255.0).astype(np.uint8)
        depth_u16 = np.rint(assets.depth * 65535.0).astype(np.uint16)
        manifest_temp = target / f".{cls.MANIFEST_NAME}-{token}.tmp"
        try:
            Image.fromarray(mask_u8, mode="L").save(target / files["mask"])
            Image.fromarray(depth_u16).save(target / files["depth"])
            np.savez_compressed(
                target / files["flow"], flow=assets.flow.astype(np.float32)
            )
            manifest = assets.manifest()
            manifest["files"] = files
            manifest_temp.write_text(
                json.dumps(manifest, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            os.replace(manifest_temp, manifest_path)
        except Exception:
            for path in [*new_paths, manifest_temp]:
                try:
                    path.unlink()
                except OSError:
                    pass
            raise

        for filename in previous_files:
            if filename not in files.values():
                try:
                    old_path = (target / str(filename)).resolve()
                    if old_path.parent == target.resolve():
                        old_path.unlink()
                except OSError:
                    pass
        return manifest_path

    @classmethod
    def load(cls, directory: str | Path) -> EffectAssets:
        source = Path(directory)
        manifest_path = source / cls.MANIFEST_NAME
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
        files = data.get("files") or {}

        mask = np.asarray(Image.open(source / files.get("mask", "mask.png")).convert("L"), dtype=np.float32)
        mask /= 255.0

        depth_raw = np.asarray(Image.open(source / files.get("depth", "depth.png")), dtype=np.float32)
        depth_scale = 65535.0 if depth_raw.max(initial=0.0) > 255.0 else 255.0
        depth = depth_raw / depth_scale

        with np.load(source / files.get("flow", "flow.npz"), allow_pickle=False) as flow_file:
            flow = np.asarray(flow_file["flow"], dtype=np.float32)

        return EffectAssets(
            version=int(data.get("version", 1)),
            effect_type=data["effect_type"],
            seed=int(data["seed"]),
            mask=mask,
            depth=depth,
            flow=flow,
            style=StyleProfile.from_dict(data.get("style")),
            textures={str(key): str(value) for key, value in (data.get("textures") or {}).items()},
            metadata=dict(data.get("metadata") or {}),
        )
