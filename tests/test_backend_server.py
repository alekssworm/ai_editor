import os
import unittest

import backend_server
from PIL import Image


class BackendServerTests(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
