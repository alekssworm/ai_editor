from __future__ import annotations

import unittest
from unittest.mock import Mock, patch

import requests

import backend_client


class BackendClientTests(unittest.TestCase):
    def test_connection_error_becomes_actionable_message(self) -> None:
        raw_error = requests.ConnectionError("HTTPConnectionPool raw details")
        with patch.object(backend_client._session, "request", side_effect=raw_error):
            with self.assertRaises(backend_client.BackendUnavailableError) as raised:
                backend_client.health(timeout=0.1)

        message = str(raised.exception)
        self.assertIn("AI backend недоступен", message)
        self.assertIn("python -m uvicorn", message)
        self.assertNotIn("HTTPConnectionPool raw details", message)

    def test_http_error_uses_backend_detail(self) -> None:
        response = Mock(status_code=503, text="")
        response.raise_for_status.side_effect = requests.HTTPError("raw HTTP error")
        response.json.return_value = {"detail": "GPU is busy"}
        with patch.object(backend_client._session, "request", return_value=response):
            with self.assertRaisesRegex(
                backend_client.BackendRequestError,
                "HTTP 503: GPU is busy",
            ):
                backend_client._req("GET", "/health", timeout=0.1)

    def test_checked_render_calls_health_before_submit(self) -> None:
        with (
            patch.object(backend_client, "health") as health,
            patch.object(backend_client, "start_svd_render", return_value="job-7") as start,
        ):
            result = backend_client.start_svd_render_checked(
                "H:/project/shapes.json",
                "H:/project/result.mp4",
                health_timeout=0.25,
            )

        self.assertEqual(result, "job-7")
        health.assert_called_once_with(timeout=0.25)
        start.assert_called_once()


if __name__ == "__main__":
    unittest.main()
