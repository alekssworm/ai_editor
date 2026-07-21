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


if __name__ == "__main__":
    unittest.main()
