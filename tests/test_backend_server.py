import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import backend_server
from PIL import Image
from pydantic import ValidationError


class BackendServerTests(unittest.TestCase):
    def test_render_request_rejects_unsafe_ranges(self) -> None:
        with self.assertRaises(ValidationError):
            backend_server.RenderRequest(
                shapes_json="shapes.json", out_mp4="result.mp4", fps=0
            )
        with self.assertRaises(ValidationError):
            backend_server.RenderRequest(
                shapes_json="shapes.json", out_mp4="result.mp4", num_frames=1000
            )

    def test_runtime_path_matches_native_platform(self) -> None:
        windows_path = "H:/project/shapes.json"

        if os.name == "nt":
            self.assertEqual(
                backend_server.runtime_path(windows_path),
                os.path.normpath(windows_path),
            )
            self.assertEqual(
                backend_server.runtime_path("/mnt/h/project/shapes.json"),
                os.path.normpath(windows_path),
            )
        else:
            self.assertEqual(
                backend_server.runtime_path(windows_path),
                "/mnt/h/project/shapes.json",
            )

    def test_health_describes_backend_runtime(self) -> None:
        health = backend_server.health()

        self.assertTrue(health["ok"])
        self.assertEqual(health["runtime"], os.name)
        self.assertEqual(health["service"], "ai_editor backend")

    def test_image_postprocessing_helpers_have_local_pil_imports(self) -> None:
        patch = Image.new("RGB", (8, 8), "blue")
        reference = Image.new("RGB", (8, 8), "red")
        mask = Image.new("L", (8, 8), 255)

        focused = backend_server._prepare_focus_patch(patch, mask)
        matched = backend_server._color_match_frame(patch, reference, mask)
        smoothed = backend_server._temporal_smooth_frames(
            [patch, reference],
            mask,
        )

        self.assertEqual(focused.size, patch.size)
        self.assertEqual(matched.size, patch.size)
        self.assertEqual(len(smoothed), 2)

    def test_mean_edge_color_supports_rectangular_images(self) -> None:
        image = Image.new("RGB", (11, 5), (10, 20, 30))

        self.assertEqual(backend_server._mean_edge_color(image), (10, 20, 30))

    def test_letterbox_preserves_portrait_aspect_ratio(self) -> None:
        portrait = Image.new("RGB", (400, 800), "green")

        canvas, content_box = backend_server._letterbox_for_svd(portrait)

        self.assertEqual(canvas.size, (1024, 576))
        left, top, right, bottom = content_box
        self.assertEqual((top, bottom), (0, 576))
        self.assertEqual(right - left, 288)

    def test_card_motion_maps_to_directional_svd_postprocessing(self) -> None:
        settings = backend_server._card_to_svd_settings(
            {
                "main": {"params": {}},
                "motion": {
                    "direction": [0, 2],
                    "strength": 7,
                    "cycles": 3,
                },
            }
        )

        self.assertEqual(settings[3], (0.0, 1.0))
        self.assertEqual(settings[4], 7.0)
        self.assertEqual(settings[5], 3)

    def test_directional_postprocessing_is_deterministic_and_loop_aligned(self) -> None:
        source = Image.new("RGB", (12, 8), "black")
        for x in range(source.width):
            for y in range(source.height):
                source.putpixel((x, y), (x * 20, y * 20, 30))
        frames = [source.copy() for _ in range(8)]

        first = backend_server._apply_directional_loop(
            frames, (1, 0), amplitude_px=3, cycles=1
        )
        second = backend_server._apply_directional_loop(
            frames, (1, 0), amplitude_px=3, cycles=1
        )

        self.assertEqual(first[0].tobytes(), source.tobytes())
        self.assertNotEqual(first[2].tobytes(), source.tobytes())
        self.assertEqual(
            [frame.tobytes() for frame in first],
            [frame.tobytes() for frame in second],
        )

    def test_directional_postprocessing_reflects_instead_of_wrapping_edges(self) -> None:
        source = Image.new("RGB", (8, 6), "black")
        for x in range(source.width):
            for y in range(source.height):
                source.putpixel((x, y), (x * 30, 0, 0))
        shifted = backend_server._apply_directional_loop(
            [source.copy() for _ in range(8)],
            (1, 0),
            amplitude_px=3,
            cycles=1,
        )[2]

        self.assertNotEqual(shifted.getpixel((0, 2)), source.getpixel((7, 2)))

    def test_ping_pong_loop_has_no_generated_end_to_start_cut(self) -> None:
        frames = [
            Image.new("RGB", (2, 2), (index * 20, 0, 0))
            for index in range(8)
        ]

        loop = backend_server._make_seamless_ping_pong(frames)

        self.assertEqual(len(loop), 8)
        self.assertEqual(loop[0].getpixel((0, 0)), (0, 0, 0))
        self.assertEqual(loop[4].getpixel((0, 0)), (140, 0, 0))
        self.assertLess(loop[-1].getpixel((0, 0))[0], 80)

    def test_status_is_copied_and_active_job_can_be_cancelled(self) -> None:
        job_id = "cancel-test"
        backend_server._jobs[job_id] = {
            "job_id": job_id,
            "state": "running",
            "progress": {"stage": "rendering"},
            "log": [],
        }
        try:
            snapshot = backend_server.svd_status(job_id)
            snapshot["progress"]["stage"] = "mutated"
            result = backend_server.svd_cancel(job_id)

            self.assertEqual(
                backend_server._jobs[job_id]["progress"]["stage"], "rendering"
            )
            self.assertTrue(backend_server._jobs[job_id]["cancel_requested"])
            self.assertEqual(result["state"], "cancelling")
        finally:
            backend_server._jobs.pop(job_id, None)

    def test_layer_cache_is_atomic_and_pruned(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            cache_dir = Path(directory)
            frame = Image.new("RGB", (3, 2), "purple")

            for index in range(4):
                path = cache_dir / f"{index}.npz"
                backend_server._save_cached_frames(str(path), [frame])
                os.utime(path, (index + 1, index + 1))

            unrelated = cache_dir / "keep.txt"
            unrelated.write_text("keep", encoding="utf-8")
            backend_server._prune_layer_cache(str(cache_dir), max_entries=2)

            self.assertEqual(
                sorted(path.name for path in cache_dir.glob("*.npz")),
                ["2.npz", "3.npz"],
            )
            self.assertTrue(unrelated.exists())
            self.assertFalse(list(cache_dir.glob("*.tmp.npz")))
            loaded = backend_server._load_cached_frames(str(cache_dir / "3.npz"))
            self.assertEqual(loaded[0].tobytes(), frame.tobytes())

    def test_render_job_reads_saved_project_flow_directions(self) -> None:
        class DummyWriter:
            def __init__(self):
                self.frames = []
                self.closed = False

            def append_data(self, frame):
                self.frames.append(frame)

            def close(self):
                self.closed = True

        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            background = base / "background.png"
            Image.new("RGB", (24, 20), "blue").save(background)
            project_path = base / "shapes.json"
            project_path.write_text(
                json.dumps(
                    {
                        "background": "background.png",
                        "shapes": [
                            {
                                "id": 3,
                                "type": "Rectangle",
                                "x": 3,
                                "y": 3,
                                "width": 14,
                                "height": 12,
                            }
                        ],
                        "shape_cards": [],
                        "flow_directions": {"3": {"x": 0, "y": 1}},
                    }
                ),
                encoding="utf-8",
            )
            request = backend_server.RenderRequest(
                shapes_json=str(project_path),
                out_mp4=str(base / "result.mp4"),
                fps=2,
                num_frames=2,
                enable_cache=False,
            )
            job_id = "flow-direction-regression"
            backend_server._jobs[job_id] = {
                "job_id": job_id,
                "state": "queued",
                "progress": {},
                "log": [],
            }
            writer = DummyWriter()
            fake_torch = SimpleNamespace(
                cuda=SimpleNamespace(is_available=lambda: False)
            )

            def fake_frames(_pipe, image, **kwargs):
                return [image.copy() for _ in range(kwargs["num_frames"])]

            def fake_get_writer(path, **_kwargs):
                Path(path).touch()
                return writer

            try:
                with (
                    patch.dict(os.environ, {"AI_BACKEND_ALLOW_CPU": "1"}),
                    patch.dict(sys.modules, {"torch": fake_torch}),
                    patch("backend_server._load_svd_pipeline", return_value=object()),
                    patch("backend_server._svd_generate_frames", side_effect=fake_frames),
                    patch("imageio.get_writer", side_effect=fake_get_writer),
                ):
                    backend_server._render_svd_job(job_id, request)

                self.assertEqual(backend_server._jobs[job_id]["state"], "done")
                self.assertEqual(len(writer.frames), 2)
                self.assertTrue(writer.closed)
            finally:
                backend_server._jobs.pop(job_id, None)


if __name__ == "__main__":
    unittest.main()
