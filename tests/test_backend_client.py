from __future__ import annotations

import unittest
from unittest.mock import Mock, patch

import requests

import backend_client


class BackendClientTests(unittest.TestCase):
    def test_render_request_uses_smooth_hq_output_defaults(self) -> None:
        with patch.object(
            backend_client,
            "_req",
            return_value={"job_id": "hq-job"},
        ) as request:
            job_id = backend_client.start_svd_render(
                "H:/project/shapes.json",
                "H:/project/result.mp4",
            )

        payload = request.call_args.kwargs["json_body"]
        self.assertEqual(job_id, "hq-job")
        self.assertEqual(payload["output_fps"], 24)
        self.assertEqual(payload["output_frames"], 72)
        self.assertEqual(payload["crf"], 18)

    def test_connection_error_becomes_actionable_message(self) -> None:
        raw_error = requests.ConnectionError("HTTPConnectionPool raw details")
        with patch.object(backend_client._session, "request", side_effect=raw_error):
            with self.assertRaises(backend_client.BackendUnavailableError) as raised:
                backend_client.health(timeout=0.1)

        message = str(raised.exception)
        self.assertIn("AI backend недоступен", message)
        self.assertIn("backend_server.py", message)
        self.assertIn(".venv", message)
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
            patch.object(
                backend_client,
                "ensure_backend_ready",
                return_value={"cuda_available": True},
            ) as ready,
            patch.object(backend_client, "start_svd_render", return_value="job-7") as start,
        ):
            result = backend_client.start_svd_render_checked(
                "H:/project/shapes.json",
                "H:/project/result.mp4",
                health_timeout=0.25,
                gpu_timeout=4.0,
            )

        self.assertEqual(result, "job-7")
        ready.assert_called_once_with(health_timeout=0.25, gpu_timeout=4.0)
        start.assert_called_once()

    def test_checked_render_autostarts_local_backend_after_connection_error(self) -> None:
        unavailable = backend_client.BackendUnavailableError("offline")
        with (
            patch.object(
                backend_client,
                "ensure_backend_ready",
                side_effect=[unavailable, {"cuda_available": True}],
            ) as ready,
            patch.object(
                backend_client,
                "try_start_local_backend",
                return_value=True,
            ) as autostart,
            patch.object(
                backend_client,
                "start_svd_render",
                return_value="job-autostart",
            ),
        ):
            result = backend_client.start_svd_render_checked(
                "H:/project/shapes.json",
                "H:/project/result.mp4",
            )

        self.assertEqual(result, "job-autostart")
        self.assertEqual(ready.call_count, 2)
        autostart.assert_called_once_with()

    def test_local_backend_launcher_waits_until_health_is_ready(self) -> None:
        process = Mock(pid=1234)
        unavailable = backend_client.BackendUnavailableError("offline")
        with (
            patch.object(backend_client, "_is_local_backend_url", return_value=True),
            patch.object(
                backend_client,
                "_backend_launch_spec",
                return_value=(["python", "backend_server.py"], "project"),
            ),
            patch.object(
                backend_client,
                "health",
                side_effect=[unavailable, {"ok": True}],
            ),
            patch.object(backend_client.subprocess, "Popen", return_value=process) as popen,
            patch.object(backend_client.atexit, "register"),
        ):
            started = backend_client.try_start_local_backend(wait_seconds=1)

        self.assertTrue(started)
        popen.assert_called_once()
        backend_client._autostart_process = None
        backend_client._autostart_token = None
        backend_client._shutdown_registered = False

    def test_owned_backend_shutdown_uses_token_and_waits_for_process(self) -> None:
        process = Mock()
        response = Mock(status_code=200)
        backend_client._autostart_process = process
        backend_client._autostart_token = "owner-secret"
        try:
            with patch.object(
                backend_client._session,
                "post",
                return_value=response,
            ) as post:
                stopped = backend_client.shutdown_local_backend(timeout=1)

            self.assertTrue(stopped)
            post.assert_called_once_with(
                f"{backend_client.BASE}/shutdown",
                headers={"X-AI-Backend-Owner": "owner-secret"},
                timeout=(0.75, 1.0),
            )
            process.wait.assert_called_once_with(timeout=1.0)
            self.assertIsNone(backend_client._autostart_process)
            self.assertIsNone(backend_client._autostart_token)
        finally:
            backend_client._autostart_process = None
            backend_client._autostart_token = None

    def test_backend_ready_rejects_cpu_only_torch(self) -> None:
        with (
            patch.object(backend_client, "health"),
            patch.object(
                backend_client,
                "gpu_info",
                return_value={"cuda_available": False, "torch": "2.9.1+cpu"},
            ),
        ):
            with self.assertRaisesRegex(
                backend_client.BackendRequestError,
                "CUDA недоступна",
            ):
                backend_client.ensure_backend_ready()

    def test_status_poll_is_quiet_in_debug_log(self) -> None:
        response = Mock(status_code=200)
        response.raise_for_status.return_value = None
        response.json.return_value = {
            "state": "running",
            "progress": {"stage": "rendering", "step": 8, "steps": 25},
        }
        with (
            patch.object(backend_client._session, "request", return_value=response),
            patch("builtins.print") as output,
        ):
            status = backend_client.get_svd_status("job-8", timeout=0.1)

        self.assertEqual(status["progress"]["step"], 8)
        output.assert_not_called()


if __name__ == "__main__":
    unittest.main()
