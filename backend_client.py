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
BASE = os.environ.get("AI_BACKEND_BASE", "http://127.0.0.1:8000")
DEBUG = os.environ.get("AI_BACKEND_DEBUG", "1") not in ("0", "false", "False", "")
LOGFILE = os.environ.get("AI_BACKEND_CLIENT_LOG", os.path.join(os.getcwd(), "backend_client.log"))
_session = requests.Session()
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
        t = (5.0, float(timeout)) if timeout is not None else None
        r = requests.request(method, url, json=json_body, timeout=t)
    except Exception as e:
        if DEBUG:
            try:
                print(f"[DEBUG] [CLIENT {rid}] REQ ERROR: {e}")
            except Exception:
                pass
        raise

    if DEBUG:
        try:
            print(f"[DEBUG] [CLIENT {rid}] RESP {r.status_code}")
        except Exception:
            pass

    r.raise_for_status()
    return r.json()

def health(timeout: float = 3.0) -> Dict[str, Any]:
    return _req("GET", "/health", timeout=timeout)
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

def get_svd_status(job_id: str, timeout: float = 5.0) -> Dict[str, Any]:
    return _req("GET", f"/svd/status/{job_id}", timeout=timeout)