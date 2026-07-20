# backend_client.py
"""
Windows-side client to call WSL backend.
Usage:
  import backend_client
  print(backend_client.gpu_info())
"""
from __future__ import annotations
import json
import os
import time
import uuid
from typing import Any, Dict, Optional
import requests

BASE = os.environ.get("AI_BACKEND_BASE", "http://127.0.0.1:8000").rstrip("/")
DEBUG = os.environ.get("AI_BACKEND_DEBUG", "1") not in ("0", "false", "False", "")
LOGFILE = os.environ.get("AI_BACKEND_CLIENT_LOG", os.path.join(os.getcwd(), "backend_client.log"))
_session = requests.Session()


class BackendClientError(RuntimeError):
    """Base error safe to display in the editor UI."""


class BackendUnavailableError(BackendClientError):
    pass


class BackendRequestError(BackendClientError):
    pass


def _backend_unavailable_message() -> str:
    return (
        f"AI backend недоступен: {BASE}\n\n"
        "Этот режим требует отдельный WSL/NVIDIA server. Запустите в WSL:\n"
        "python -m uvicorn backend_server:app --host 0.0.0.0 --port 8000\n\n"
        "Локальный deterministic Preview работает без сервера."
    )


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
def _req(method: str, path: str, *, json_body: Any = None, timeout: float = 30.0) -> Dict[str, Any]:
    url = f"{BASE}{path}"
    rid = uuid.uuid4().hex[:8]

    if DEBUG:
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

    if DEBUG:
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


def gpu_info(timeout: float = 3.0) -> Dict[str, Any]:
    return _req("GET", "/gpu", timeout=timeout)


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


def start_svd_render_checked(*args, health_timeout: float = 2.0, **kwargs) -> str:
    """Fail fast with an actionable error before submitting a GPU render job."""
    health(timeout=health_timeout)
    return start_svd_render(*args, **kwargs)


def get_svd_status(job_id: str, timeout: float = 5.0) -> Dict[str, Any]:
    return _req("GET", f"/svd/status/{job_id}", timeout=timeout)
