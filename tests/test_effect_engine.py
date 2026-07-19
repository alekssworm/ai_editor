from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import numpy as np
from PIL import Image

from effect_engine.models import EffectAssets
from effect_engine.preparation import PreparationPipeline
from effect_engine.project import prepare_project_shape
from effect_engine.renderer import DeterministicEffectEngine
from effect_engine.storage import EffectAssetStore


def sample_image(width: int = 48, height: int = 36) -> Image.Image:
    y, x = np.mgrid[0:height, 0:width]
    rgb = np.stack(
        (
            (x * 7 + y * 2) % 256,
            (x * 3 + y * 9) % 256,
            (x * 11 + y * 5) % 256,
        ),
        axis=-1,
    ).astype(np.uint8)
    return Image.fromarray(rgb, mode="RGB")


class EffectEngineTests(unittest.TestCase):
    def setUp(self) -> None:
        self.image = sample_image()
        self.mask = np.zeros((self.image.height, self.image.width), dtype=np.float32)
        self.mask[5:31, 6:43] = 1.0
        self.pipeline = PreparationPipeline()

    def prepare(self, seed: int = 42) -> EffectAssets:
        return self.pipeline.prepare(
            self.image,
            self.mask,
            effect_type="water",
            seed=seed,
            direction=(1.0, 0.2),
        )

    def test_effect_assets_storage_round_trip(self) -> None:
        assets = self.prepare()
        with tempfile.TemporaryDirectory() as directory:
            EffectAssetStore.save(assets, directory)
            restored = EffectAssetStore.load(directory)

        self.assertEqual(restored.effect_type, "water")
        self.assertEqual(restored.seed, 42)
        self.assertEqual(restored.size, self.image.size)
        self.assertGreater(len(restored.style.palette), 0)
        np.testing.assert_allclose(restored.mask, assets.mask, atol=1.0 / 255.0)
        np.testing.assert_allclose(restored.depth, assets.depth, atol=1.0 / 65535.0)
        np.testing.assert_array_equal(restored.flow, assets.flow)

    def test_water_renderer_is_seeded_and_periodic(self) -> None:
        assets = self.prepare(seed=123)
        engine = DeterministicEffectEngine()
        at_zero = np.asarray(engine.render_frame(self.image, assets, 0.0))
        at_one = np.asarray(engine.render_frame(self.image, assets, 1.0))
        repeated = np.asarray(engine.render_frame(self.image, assets, 0.0))
        other_phase = np.asarray(engine.render_frame(self.image, assets, 0.25))

        np.testing.assert_array_equal(at_zero, at_one)
        np.testing.assert_array_equal(at_zero, repeated)
        self.assertFalse(np.array_equal(at_zero, other_phase))

        other_seed = self.prepare(seed=124)
        seeded_output = np.asarray(engine.render_frame(self.image, other_seed, 0.0))
        self.assertFalse(np.array_equal(at_zero, seeded_output))

    def test_frame_sequence_does_not_duplicate_endpoint(self) -> None:
        frames = DeterministicEffectEngine().render_frames(self.image, self.prepare(), 12)
        self.assertEqual(len(frames), 12)
        self.assertFalse(np.array_equal(np.asarray(frames[0]), np.asarray(frames[-1])))

    def test_project_adapter_supports_relative_background_and_polygon(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.image.save(root / "background.png")
            project = {
                "background": "background.png",
                "shapes": [
                    {
                        "id": 7,
                        "type": "Polygon",
                        "points": [
                            {"x": 4, "y": 4},
                            {"x": 42, "y": 7},
                            {"x": 35, "y": 31},
                            {"x": 8, "y": 28},
                        ],
                        "color": "#00aaff",
                        "parent_id": None,
                    }
                ],
                "shape_cards": [{"id": 7, "tool_type": "water", "main": None, "sub": []}],
            }
            project_path = root / "shapes.json"
            project_path.write_text(json.dumps(project), encoding="utf-8")

            assets, target = prepare_project_shape(
                project_path,
                7,
                seed=9,
                direction=(0.8, 0.3),
            )

            self.assertEqual(assets.effect_type, "water")
            self.assertEqual(assets.metadata["shape_id"], 7)
            self.assertTrue((target / "manifest.json").exists())
            self.assertGreater(float(assets.mask.max()), 0.9)


if __name__ == "__main__":
    unittest.main()
