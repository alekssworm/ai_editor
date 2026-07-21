# backend_client.py
"""
Editor-side client for the local or remote AI backend.
Usage:
  import backend_client
  print(backend_client.gpu_info())
"""
from __future__ import annotations
import atexit
import json
import os
from pathlib import Path
import secrets
import subprocess
import sys
import threading
import time
import uuid
from typing import Any, Dict, Optional
from urllib.parse import urlparse
import requests

BASE = os.environ.get("AI_BACKEND_BASE", "http://127.0.0.1:8000").rstrip("/")
DEBUG = os.environ.get("AI_BACKEND_DEBUG", "1") not in ("0", "false", "False", "")
LOGFILE = os.environ.get("AI_BACKEND_CLIENT_LOG", os.path.join(os.getcwd(), "backend_client.log"))
_session = requests.Session()
_autostart_lock = threading.Lock()
_autostart_process = None
_autostart_token = None
_shutdown_registered = False


class BackendClientError(RuntimeError):
    """Base error safe to display in the editor UI."""


class BackendUnavailableError(BackendClientError):
    pass


class BackendRequestError(BackendClientError):
    pass


def _backend_unavailable_message(*, autostart_attempted: bool = False) -> str:
    prefix = (
        "Автозапуск локального backend не удался.\n\n"
        if autostart_attempted
        else ""
    )
    return prefix + (
        f"AI backend недоступен: {BASE}\n\n"
        "Запустите backend в отдельном терминале из папки проекта:\n"
        ".\\.venv\\Scripts\\python.exe backend_server.py\n\n"
        "Для WSL/Linux: python backend_server.py\n"
        "Если отсутствует uvicorn: python -m pip install uvicorn\n\n"
        "Локальный deterministic Preview работает без сервера."
    )


def _is_local_backend_url() -> bool:
    try:
        host = (urlparse(BASE).hostname or "").lower()
    except ValueError:
        return False
    return host in {"127.0.0.1", "localhost", "::1"}


def _win_to_wsl_project_path(path: Path) -> str:
    resolved = path.resolve()
    drive = resolved.drive.rstrip(":").lower()
    if len(drive) != 1:
        raise ValueError(f"WSL autostart requires a drive path: {resolved}")
    suffix = resolved.as_posix()[2:].lstrip("/")
    return f"/mnt/{drive}/{suffix}"


def _backend_launch_spec(owner_token: str):
    """Return the preferred local backend command and its working directory."""
    project_dir = Path(__file__).resolve().parent
    if os.name == "nt":
        # Linux venv executables are symlinks. Path.exists() can raise WinError
        # 1920 when Windows tries to follow their /usr/bin target, so inspect
        # the containing directory instead.
        wsl_bin = project_dir / ".venv-wsl" / "bin"
        if wsl_bin.is_dir():
            return (
                [
                    "wsl.exe",
                    "--cd",
                    _win_to_wsl_project_path(project_dir),
                    "--",
                    "env",
                    f"AI_BACKEND_OWNER_TOKEN={owner_token}",
                    "AI_BACKEND_IDLE_TIMEOUT=90",
                    "./.venv-wsl/bin/python",
                    "backend_server.py",
                ],
                None,
            )

        windows_python = project_dir / ".venv" / "Scripts" / "python.exe"
        if windows_python.exists():
            return (
                [str(windows_python), "backend_server.py"],
                str(project_dir),
            )
        return ([sys.executable, "backend_server.py"], str(project_dir))

    local_python = project_dir / ".venv-wsl" / "bin" / "python"
    if not local_python.exists():
        local_python = project_dir / ".venv" / "bin" / "python"
    executable = str(local_python) if local_python.exists() else sys.executable
    return ([executable, "backend_server.py"], str(project_dir))


def try_start_local_backend(wait_seconds: float = 25.0) -> bool:
    """Start this project's backend when BASE points at the local machine."""
    global _autostart_process, _autostart_token, _shutdown_registered
    enabled = os.environ.get("AI_BACKEND_AUTOSTART", "1") not in {
        "0",
        "false",
        "False",
        "",
    }
    if not enabled or not _is_local_backend_url():
        return False

    with _autostart_lock:
        # Another render request may have started the service while we waited.
        try:
            health(timeout=0.75)
            return True
        except BackendUnavailableError:
            pass

        owner_token = secrets.token_urlsafe(32)
        command, cwd = _backend_launch_spec(owner_token)
        display_command = [
            "AI_BACKEND_OWNER_TOKEN=<hidden>"
            if part.startswith("AI_BACKEND_OWNER_TOKEN=")
            else part
            for part in command
        ]
        _log(f"autostart backend: {' '.join(display_command)}")
        child_environment = os.environ.copy()
        child_environment["AI_BACKEND_OWNER_TOKEN"] = owner_token
        child_environment["AI_BACKEND_IDLE_TIMEOUT"] = "90"
        popen_kwargs = {
            "cwd": cwd,
            "env": child_environment,
            "stdin": subprocess.DEVNULL,
            "stdout": subprocess.DEVNULL,
            "stderr": subprocess.DEVNULL,
        }
        if os.name == "nt":
            startup_info = subprocess.STARTUPINFO()
            startup_info.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startup_info.wShowWindow = subprocess.SW_HIDE
            popen_kwargs["startupinfo"] = startup_info
            popen_kwargs["creationflags"] = (
                subprocess.CREATE_NO_WINDOW | subprocess.CREATE_NEW_PROCESS_GROUP
            )
        try:
            process = subprocess.Popen(command, **popen_kwargs)
            _autostart_process = process
            _autostart_token = owner_token
            if not _shutdown_registered:
                atexit.register(shutdown_local_backend)
                _shutdown_registered = True
        except (OSError, ValueError) as error:
            _log(f"backend autostart failed: {error}")
            return False

        deadline = time.monotonic() + max(1.0, float(wait_seconds))
        while time.monotonic() < deadline:
            try:
                health(timeout=1.0)
                _log(f"backend autostart ready (pid={process.pid})")
                return True
            except BackendUnavailableError:
                if process.poll() is not None:
                    _log(f"backend autostart exited with code {process.returncode}")
                    _autostart_process = None
                    _autostart_token = None
                    return False
                time.sleep(0.4)
        _log("backend autostart timed out")
        return False


def shutdown_local_backend(timeout: float = 3.0) -> bool:
    """Stop only the backend process started and owned by this editor process."""
    global _autostart_process, _autostart_token

    process = _autostart_process
    token = _autostart_token
    if process is None or not token:
        return False

    stopped = False
    try:
        response = _session.post(
            f"{BASE}/shutdown",
            headers={"X-AI-Backend-Owner": token},
            timeout=(0.75, max(1.0, float(timeout))),
        )
        stopped = response.status_code == 200
    except requests.RequestException:
        pass

    try:
        process.wait(timeout=max(0.5, float(timeout)))
        stopped = True
    except subprocess.TimeoutExpired:
        try:
            process.terminate()
        except OSError:
            pass
    finally:
        _autostart_process = None
        _autostart_token = None
    return stopped


def _log(msg: str, data: Any = None) -> None:
    if not DEBUG:
        return
    ts = time.strftime("%H:%M:%S")
    line = f"[CLIENT {ts}] {msg}"
    print(line, flush=True)
    # also write to logfile (best-effort)
    try:
        with open(LOGFILE, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass
    if data is not None:
        try:
            dump = json.dumps(data, ensure_ascii=False, indent=2)
        except Exception:
            dump = str(data)
        print(dump, flush=True)
        try:
            with open(LOGFILE, "a", encoding="utf-8") as f:
                f.write(dump + "\n")
        except Exception:
            pass
def _req(
    method: str,
    path: str,
    *,
    json_body: Any = None,
    timeout: float = 30.0,
    quiet: bool = False,
) -> Dict[str, Any]:
    url = f"{BASE}{path}"
    rid = uuid.uuid4().hex[:8]

    if DEBUG and not quiet:
        try:
            print(f"[DEBUG] [CLIENT {rid}] {method} {url}")
            if isinstance(json_body, dict):
                print(f"[DEBUG] [CLIENT {rid}] shapes_json={json_body.get('shapes_json')} out_mp4={json_body.get('out_mp4')}")
        except Exception:
            pass

    try:
        if timeout is None:
            request_timeout = None
        else:
            timeout_value = max(0.1, float(timeout))
            request_timeout = (min(2.0, timeout_value), timeout_value)
        response = _session.request(
            method,
            url,
            json=json_body,
            timeout=request_timeout,
        )
    except (requests.ConnectionError, requests.Timeout) as error:
        if DEBUG:
            print(f"[DEBUG] [CLIENT {rid}] backend unavailable: {type(error).__name__}")
        raise BackendUnavailableError(_backend_unavailable_message()) from error
    except requests.RequestException as error:
        raise BackendRequestError(f"Ошибка запроса к AI backend: {error}") from error

    if DEBUG and not quiet:
        print(f"[DEBUG] [CLIENT {rid}] RESP {response.status_code}")

    try:
        response.raise_for_status()
    except requests.HTTPError as error:
        try:
            body = response.json()
            detail = body.get("detail") if isinstance(body, dict) else body
        except ValueError:
            detail = response.text.strip()
        suffix = f": {detail}" if detail else ""
        raise BackendRequestError(
            f"AI backend вернул HTTP {response.status_code}{suffix}"
        ) from error

    try:
        payload = response.json()
    except ValueError as error:
        raise BackendRequestError("AI backend вернул некорректный JSON") from error
    if not isinstance(payload, dict):
        raise BackendRequestError("AI backend вернул неожиданный формат ответа")
    return payload


def health(timeout: float = 3.0) -> Dict[str, Any]:
    result = _req("GET", "/health", timeout=timeout)
    if result.get("ok") is not True:
        raise BackendRequestError(f"AI backend health-check failed: {result}")
    return result


def gpu_info(timeout: float = 20.0) -> Dict[str, Any]:
    return _req("GET", "/gpu", timeout=timeout)


def ensure_backend_ready(
    *, health_timeout: float = 2.0, gpu_timeout: float = 20.0
) -> Dict[str, Any]:
    """Verify that the API is reachable and has a CUDA-capable PyTorch build."""
    health(timeout=health_timeout)
    gpu = gpu_info(timeout=gpu_timeout)
    if gpu.get("cuda_available") is not True:
        details = gpu.get("error") or gpu.get("torch") or "CUDA не обнаружена"
        raise BackendRequestError(
            "AI backend запущен, но CUDA недоступна. "
            f"Установите CUDA-сборку PyTorch для NVIDIA GPU. Детали: {details}"
        )
    return gpu


def start_svd_render(
    shapes_json: Optional[str] = None,
    out_mp4: Optional[str] = None,
    masks_dir: Optional[str] = None,
    pieces_dir: Optional[str] = None,
    *,
    shapes_json_path: Optional[str] = None,
    out_mp4_path: Optional[str] = None,
    fps: int = 7,
    num_frames: int = 25,
    pad: int = 32,
    feather_px: int = 5,
    seed_base: int = 123,
    render_mode: str = "final",
    layer_render: bool = True,
    enable_cache: bool = True,
    timeout: float = 30.0,
) -> str:
    if shapes_json is None and shapes_json_path is not None:
        shapes_json = shapes_json_path
    if out_mp4 is None and out_mp4_path is not None:
        out_mp4 = out_mp4_path
    if not shapes_json or not out_mp4:
        raise ValueError("start_svd_render: shapes_json/out_mp4 required")

    payload = {
        "shapes_json": str(shapes_json),
        "out_mp4": str(out_mp4),
        "fps": int(fps),
        "num_frames": int(num_frames),
        "pad": int(pad),
        "feather_px": int(feather_px),
        "seed_base": int(seed_base),
        "render_mode": str(render_mode),
        "layer_render": bool(layer_render),
        "enable_cache": bool(enable_cache),
    }
    if masks_dir is not None:
        payload["masks_dir"] = str(masks_dir)
    if pieces_dir is not None:
        payload["pieces_dir"] = str(pieces_dir)

    res = _req("POST", "/svd/render", json_body=payload, timeout=timeout)
    job_id = res.get("job_id") if isinstance(res, dict) else None
    if not job_id:
        raise RuntimeError(f"Backend did not return job_id: {res}")
    return str(job_id)


def start_svd_render_checked(
    *args,
    health_timeout: float = 2.0,
    gpu_timeout: float = 20.0,
    **kwargs,
) -> str:
    """Fail fast with an actionable error before submitting a GPU render job."""
    try:
        ensure_backend_ready(
            health_timeout=health_timeout,
            gpu_timeout=gpu_timeout,
        )
    except BackendUnavailableError as error:
        if not try_start_local_backend():
            raise BackendUnavailableError(
                _backend_unavailable_message(autostart_attempted=True)
            ) from error
        ensure_backend_ready(
            health_timeout=health_timeout,
            gpu_timeout=gpu_timeout,
        )
    return start_svd_render(*args, **kwargs)


def get_svd_status(job_id: str, timeout: float = 5.0) -> Dict[str, Any]:
    return _req("GET", f"/svd/status/{job_id}", timeout=timeout, quiet=True)


def cancel_svd_render(job_id: str, timeout: float = 5.0) -> Dict[str, Any]:
    if not str(job_id or "").strip():
        raise ValueError("cancel_svd_render: job_id required")
    return _req(
        "POST",
        f"/svd/cancel/{job_id}",
        timeout=timeout,
        quiet=True,
    )
