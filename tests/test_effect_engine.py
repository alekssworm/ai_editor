from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np
from PIL import Image

from effect_engine.cli import resolve_render_params
from effect_engine.models import ASSET_VERSION, EffectAssets
from effect_engine.preparation import (
    PreparationPipeline,
    TransformersDepthEstimator,
    TransformersMaskRefiner,
    create_preparation_pipeline,
)
from effect_engine.preview import build_project_preview, renderer_params_from_card
from effect_engine.preset_registry import PresetRegistry, default_preset_registry
from effect_engine.project import (
    load_project,
    normalize_direction,
    prepare_project_shape,
    project_effect_overrides,
    project_flow_direction,
    project_flow_guides,
    serialize_effect_overrides,
    serialize_flow_directions,
    serialize_flow_guides,
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
        np.testing.assert_allclose(restored.flow, assets.flow, atol=1e-6)
        np.testing.assert_allclose(restored.speed, assets.speed, atol=1.0 / 255.0)
        np.testing.assert_allclose(
            restored.obstacles, assets.obstacles, atol=1.0 / 255.0
        )
        np.testing.assert_allclose(restored.foam, assets.foam, atol=1.0 / 255.0)

    def test_optional_ai_providers_return_editable_map_proposals(self) -> None:
        rough = np.zeros(self.mask.shape, dtype=np.float32)
        rough[8:28, 10:38] = 1.0
        candidate = np.zeros(self.mask.shape, dtype=np.uint8)
        candidate[9:27, 11:37] = 1
        mask_provider = TransformersMaskRefiner(feather_radius=0)
        mask_provider._pipeline = lambda _image: {"masks": [candidate]}
        refined = mask_provider.refine(np.asarray(self.image), rough)

        depth_provider = TransformersDepthEstimator()
        depth_provider._pipeline = lambda _image: {
            "depth": np.tile(
                np.linspace(0.0, 1.0, self.image.width, dtype=np.float32),
                (self.image.height, 1),
            )
        }
        depth = depth_provider.estimate(np.asarray(self.image), refined)

        self.assertGreater(float(refined[15, 20]), 0.9)
        self.assertEqual(float(refined[0, 0]), 0.0)
        self.assertAlmostEqual(float(depth.min()), 0.0, places=5)
        self.assertAlmostEqual(float(depth.max()), 1.0, places=5)
        self.assertEqual(
            create_preparation_pipeline(use_ai=False).mask_refiner.name,
            "morphology-v1",
        )

    def test_version_one_flow_magnitude_migrates_to_speed_map(self) -> None:
        flow = np.zeros((*self.mask.shape, 2), dtype=np.float32)
        flow[..., 0] = 0.4
        assets = EffectAssets(
            version=1,
            effect_type="water",
            seed=1,
            mask=self.mask,
            depth=self.mask,
            flow=flow,
        )

        self.assertEqual(assets.version, ASSET_VERSION)
        self.assertAlmostEqual(float(assets.speed.max()), 0.4, places=6)
        self.assertAlmostEqual(float(assets.flow[..., 0].max()), 1.0, places=6)
        self.assertEqual(float(assets.obstacles.max()), 0.0)
        self.assertEqual(float(assets.foam.max()), 0.0)

    def test_effect_asset_manifest_switch_is_atomic_and_cleans_old_files(self) -> None:
        assets = self.prepare()
        with tempfile.TemporaryDirectory() as directory:
            manifest_path = EffectAssetStore.save(assets, directory)
            first_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            first_files = set(first_manifest["files"].values())

            EffectAssetStore.save(self.prepare(seed=99), directory)
            second_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            second_files = set(second_manifest["files"].values())

            self.assertTrue(first_files.isdisjoint(second_files))
            self.assertTrue(all((Path(directory) / name).exists() for name in second_files))
            self.assertTrue(all(not (Path(directory) / name).exists() for name in first_files))
            self.assertFalse(list(Path(directory).glob(".manifest.json-*.tmp")))

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
        original = np.asarray(self.image)
        np.testing.assert_array_equal(
            at_zero[assets.mask <= 0.01], original[assets.mask <= 0.01]
        )

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
            flow_speed = np.linalg.norm(assets.flow, axis=-1)
            self.assertTrue(np.all(flow_speed <= 1.0 + 1e-5))
            self.assertGreater(float(flow_speed[assets.mask > 0.5].mean()), 0.5)
            self.assertEqual(float(flow_speed[assets.mask <= 0.01].max()), 0.0)
            normalized_flow = assets.flow / np.maximum(flow_speed[..., None], 1e-6)
            self.assertAlmostEqual(
                float(normalized_flow[assets.mask > 0.5, 0].mean()), 0.0, delta=0.08
            )
            self.assertLess(
                float(normalized_flow[assets.mask > 0.5, 1].mean()), -0.95
            )
            self.assertGreater(float(assets.depth.std()), 0.001)

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

    def test_flow_guides_round_trip_and_steer_local_regions(self) -> None:
        serialized = serialize_flow_guides(
            {
                4: [
                    {"start": [12, 12], "end": [12, 28]},
                    {"start": {"x": 36, "y": 28}, "end": {"x": 36, "y": 12}},
                    {"start": [1, 1], "end": [1, 1]},
                ]
            },
            {4},
        )
        project = {"flow_guides": serialized}

        self.assertEqual(len(serialized["4"]), 2)
        self.assertEqual(project_flow_guides(project, 4), serialized["4"])

        assets = self.pipeline.prepare(
            self.image,
            self.mask,
            effect_type="water",
            seed=10,
            direction=(1.0, 0.0),
            guides=serialized["4"],
        )
        speed = np.maximum(np.linalg.norm(assets.flow, axis=-1), 1e-6)
        direction = assets.flow / speed[..., None]
        self.assertGreater(float(direction[18, 12, 1]), 0.2)
        self.assertLess(float(direction[18, 36, 1]), -0.2)
        self.assertEqual(assets.metadata["flow_guides"], serialized["4"])

    def test_cubic_flow_curve_changes_direction_along_its_path(self) -> None:
        full_mask = np.ones(self.mask.shape, dtype=np.float32)
        assets = self.pipeline.prepare(
            self.image,
            full_mask,
            effect_type="water",
            seed=4,
            direction=(1.0, 0.0),
            guides=[
                {
                    "start": [6, 6],
                    "control1": [6, 29],
                    "control2": [40, 29],
                    "end": [40, 6],
                }
            ],
        )

        self.assertGreater(float(assets.flow[10, 7, 1]), 0.2)
        self.assertLess(float(assets.flow[10, 39, 1]), -0.2)

    def test_manual_map_zones_are_separate_from_ai_proposals(self) -> None:
        full_mask = np.ones(self.mask.shape, dtype=np.float32)
        overrides = {
            "speed_zones": [
                {"center": [12, 18], "radius": 8, "value": 0.2},
                {"center": [36, 18], "radius": 8, "value": 1.5},
            ],
            "obstacle_zones": [
                {"center": [24, 18], "radius": 7, "value": 1.0}
            ],
            "foam_zones": [
                {"center": [36, 18], "radius": 7, "value": 1.0}
            ],
            "depth_zones": [
                {"center": [6, 18], "radius": 5, "value": 0.9}
            ],
        }
        baseline = self.pipeline.prepare(
            self.image,
            full_mask,
            effect_type="water",
            seed=5,
            direction=(1.0, 0.0),
        )
        assets = self.pipeline.prepare(
            self.image,
            full_mask,
            effect_type="water",
            seed=5,
            direction=(1.0, 0.0),
            manual_overrides=overrides,
        )

        self.assertLess(float(assets.speed[18, 12]), 0.3)
        self.assertGreater(
            float(assets.speed[18, 36]),
            float(baseline.speed[18, 36]) * 1.2,
        )
        self.assertGreater(float(assets.obstacles[18, 24]), 0.95)
        self.assertLess(float(assets.speed[18, 24]), 0.05)
        self.assertGreater(float(assets.foam[18, 36]), 0.95)
        self.assertGreater(float(assets.depth[18, 6]), 0.85)
        self.assertEqual(
            assets.metadata["asset_layers"]["manual_overrides"]["foam_zones"],
            1,
        )

    def test_manual_mask_zones_override_the_ai_mask_proposal(self) -> None:
        assets = self.pipeline.prepare(
            self.image,
            self.mask,
            effect_type="water",
            seed=6,
            direction=(1.0, 0.0),
            manual_overrides={
                "mask_add_zones": [
                    {"center": [2, 2], "radius": 4, "value": 1.0}
                ],
                "mask_remove_zones": [
                    {"center": [20, 16], "radius": 4, "value": 1.0}
                ],
            },
        )

        self.assertGreater(float(assets.mask[2, 2]), 0.95)
        self.assertLess(float(assets.mask[16, 20]), 0.05)

    def test_effect_override_zones_round_trip(self) -> None:
        serialized = serialize_effect_overrides(
            {
                9: {
                    "speed_zones": [
                        {"center": [5, 6], "radius": 12, "value": 1.5}
                    ],
                    "obstacle_zones": [
                        {"center": [8, 9], "radius": 4, "value": 1}
                    ],
                }
            },
            {9},
        )

        restored = project_effect_overrides(
            {"effect_overrides": serialized}, 9
        )
        self.assertEqual(restored, serialized["9"])

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

    def test_numeric_motion_settings_override_strength_and_keep_whole_cycles(self) -> None:
        card = {
            "tool_type": "water",
            "main": {"key": "main_river", "params": {"intensity": "strong"}},
            "motion": {"strength": 9, "cycles": 3},
        }

        params = renderer_params_from_card(card)

        self.assertEqual(params["strength"], 9.0)
        self.assertEqual(params["cycles"], 3.0)

    def test_motion_profile_caps_values_that_create_rubbery_water(self) -> None:
        params = renderer_params_from_card(
            {
                "tool_type": "water",
                "preset_id": "still_water",
                "motion": {"strength": 20, "cycles": 8},
            }
        )

        self.assertEqual(params["strength"], 4.0)
        self.assertEqual(params["cycles"], 2.0)

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
            flow_speed = np.linalg.norm(stored.flow, axis=-1)
            normalized_flow = stored.flow / np.maximum(flow_speed[..., None], 1e-6)
            self.assertGreater(float(flow_speed[stored.mask > 0.5].mean()), 0.5)
            self.assertEqual(float(flow_speed[stored.mask <= 0.01].max()), 0.0)
            self.assertAlmostEqual(
                float(normalized_flow[stored.mask > 0.5, 0].mean()), 0.0, delta=0.08
            )
            self.assertLess(
                float(normalized_flow[stored.mask > 0.5, 1].mean()), -0.95
            )
            self.assertEqual(stored.metadata["direction"], [0.0, -1.0])

    def test_mp4_export_streams_hq_frames_without_duplicate_endpoint(self) -> None:
        class DummyWriter:
            def __init__(self, path: Path) -> None:
                path.touch()
                self.frames = []
                self.closed = False

            def append_data(self, frame) -> None:
                self.frames.append(frame.copy())

            def close(self) -> None:
                self.closed = True

        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "loop.mp4"
            writer = None
            writer_kwargs = {}

            def fake_writer(path, **kwargs):
                nonlocal writer, writer_kwargs
                writer_kwargs = kwargs
                writer = DummyWriter(Path(path))
                return writer

            with patch("effect_engine.renderer.imageio.get_writer", side_effect=fake_writer):
                result = DeterministicEffectEngine().export_mp4(
                    self.image,
                    self.prepare(),
                    output,
                    frame_count=6,
                    fps=24,
                    crf=17,
                )

            self.assertEqual(result, output)
            self.assertTrue(output.exists())
            self.assertIsNotNone(writer)
            self.assertEqual(len(writer.frames), 6)
            self.assertFalse(np.array_equal(writer.frames[0], writer.frames[-1]))
            self.assertTrue(writer.closed)
            self.assertEqual(writer_kwargs["fps"], 24)
            self.assertIn("17", writer_kwargs["ffmpeg_params"])


if __name__ == "__main__":
    unittest.main()
