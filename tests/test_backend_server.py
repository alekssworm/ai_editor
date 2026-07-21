import os
import unittest

import backend_server


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


if __name__ == "__main__":
    unittest.main()
