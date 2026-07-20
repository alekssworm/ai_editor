from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import numpy as np
from PIL import Image

from effect_engine.cli import resolve_render_params
from effect_engine.models import EffectAssets
from effect_engine.preparation import PreparationPipeline
from effect_engine.preview import build_project_preview, renderer_params_from_card
from effect_engine.preset_registry import PresetRegistry, default_preset_registry
from effect_engine.project import (
    load_project,
    normalize_direction,
    prepare_project_shape,
    project_flow_direction,
    serialize_flow_directions,
)
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
                "flow_directions": {"7": {"x": 0, "y": -2}},
            }
            project_path = root / "shapes.json"
            project_path.write_text(json.dumps(project), encoding="utf-8")

            assets, target = prepare_project_shape(
                project_path,
                7,
                seed=9,
            )

            self.assertEqual(assets.effect_type, "water")
            self.assertEqual(assets.metadata["shape_id"], 7)
            self.assertEqual(assets.metadata["preset_id"], "river")
            self.assertEqual(assets.metadata["renderer_params"]["strength"], 4.5)
            self.assertTrue((target / "manifest.json").exists())
            self.assertGreater(float(assets.mask.max()), 0.9)
            np.testing.assert_allclose(assets.flow[..., 0], 0.0)
            np.testing.assert_allclose(assets.flow[..., 1], -1.0)

    def test_flow_direction_round_trip_and_project_lookup(self) -> None:
        serialized = serialize_flow_directions(
            {3: (3.0, 4.0), "5": {"x": 0, "y": -2}, 9: (0, 0)},
            {3, 5, 9},
        )
        project = {"flow_directions": serialized, "shapes": []}

        self.assertEqual(serialized["3"], {"x": 0.6, "y": 0.8})
        self.assertNotIn("9", serialized)
        self.assertEqual(project_flow_direction(project, 5), (0.0, -1.0))
        self.assertIsNone(normalize_direction({"x": "bad", "y": 1}))

    def test_water_card_settings_are_mapped_to_renderer_params(self) -> None:
        card = {
            "tool_type": "water",
            "main": {
                "key": "main_waterfall",
                "params": {
                    "intensity": "high",
                    "power": "normal",
                    "opacity": "low",
                    "randomness": "high",
                },
            },
        }

        params = renderer_params_from_card(card)

        self.assertAlmostEqual(params["strength"], 8.7)
        self.assertAlmostEqual(params["opacity"], 0.45)
        self.assertLess(params["secondary_wavelength"], 24.0)

    def test_builtin_presets_support_ids_aliases_and_defaults(self) -> None:
        registry = default_preset_registry()

        self.assertEqual(registry.resolve("water").preset_id, "river")
        self.assertEqual(registry.resolve("water", "main_waterfall").preset_id, "waterfall")
        self.assertEqual(registry.resolve("water", "main_Still_water").preset_id, "still_water")
        self.assertEqual(
            [preset.preset_id for preset in registry.list("water")],
            ["fast_river", "river", "still_water", "waterfall"],
        )

        explicit_card = {
            "tool_type": "water",
            "preset_id": "still_water",
            "main": {"key": "main_waterfall", "params": {}},
        }
        self.assertEqual(renderer_params_from_card(explicit_card)["strength"], 2.0)

    def test_preset_registry_rejects_invalid_json(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "invalid.json"
            path.write_text(
                json.dumps(
                    {
                        "id": "broken",
                        "effect_type": "water",
                        "label": "Broken",
                        "params": {"strength": "very"},
                    }
                ),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "not numeric"):
                PresetRegistry.from_directory(directory)

            path.write_text(
                json.dumps(
                    {
                        "id": "no_default",
                        "effect_type": "water",
                        "label": "No default",
                        "params": {"strength": 2.0},
                    }
                ),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "Missing default preset"):
                PresetRegistry.from_directory(directory)

    def test_cli_render_uses_asset_preset_and_explicit_overrides(self) -> None:
        assets = self.prepare()
        assets.metadata["preset_id"] = "waterfall"
        assets.metadata["renderer_params"] = {"strength": 8.0, "opacity": 0.6}

        self.assertEqual(resolve_render_params(assets)["strength"], 8.0)
        river = resolve_render_params(assets, preset_id="river")
        self.assertEqual(river["strength"], 4.5)
        overridden = resolve_render_params(assets, preset_id="river", opacity=0.25)
        self.assertEqual(overridden["opacity"], 0.25)

    def test_future_project_schema_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "shapes.json"
            path.write_text(json.dumps({"schema_version": 999}), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "Unsupported project schema_version"):
                load_project(path)

    def test_project_preview_keeps_full_assets_and_downscales_frames(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.image.save(root / "background.png")
            project = {
                "background": "background.png",
                "shapes": [
                    {
                        "id": 3,
                        "type": "Rectangle",
                        "x": 5,
                        "y": 4,
                        "width": 35,
                        "height": 25,
                    }
                ],
                "shape_cards": [
                    {
                        "id": 3,
                        "tool_type": "water",
                        "main": {
                            "key": "main_river",
                            "name": "river",
                            "params": {"intensity": "normal", "opacity": "high"},
                        },
                        "sub": [],
                    }
                ],
            }
            project_path = root / "shapes.json"
            project_path.write_text(json.dumps(project), encoding="utf-8")

            result = build_project_preview(
                project_path,
                3,
                direction_override=(0.0, -3.0),
                frame_count=6,
                fps=10,
                max_dimension=24,
                seed=17,
            )
            stored = EffectAssetStore.load(result.assets_dir)

            self.assertEqual(len(result.frames), 6)
            self.assertEqual(result.frames[0].size, (24, 18))
            self.assertEqual(stored.size, self.image.size)
            self.assertEqual(stored.seed, 17)
            self.assertEqual(result.params["opacity"], 1.0)
            self.assertEqual(result.preset_id, "river")
            self.assertEqual(stored.metadata["preset_id"], "river")
            np.testing.assert_allclose(stored.flow[..., 0], 0.0)
            np.testing.assert_allclose(stored.flow[..., 1], -1.0)
            self.assertEqual(stored.metadata["direction"], [0.0, -1.0])


if __name__ == "__main__":
    unittest.main()
