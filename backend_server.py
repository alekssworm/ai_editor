
"""
WSL backend for SVD video generation on NVIDIA GPU.

Endpoints:
  GET  /health
  GET  /gpu
  POST /svd/render        -> start render, returns {"job_id": "..."}
  GET  /svd/status/{id}   -> get status/progress/result

This file is designed to run inside WSL venv:
  python -m uvicorn backend_server:app --host 0.0.0.0 --port 8000 --log-level info
"""
from __future__ import annotations

import json
import hashlib
import logging
import os
import re
import time
import uuid
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel, Field
from concurrent.futures import ThreadPoolExecutor

app = FastAPI(title="ai_editor backend", version="1.0")

# -----------------------
# Logging
# -----------------------
LOG_LEVEL = os.environ.get("AI_BACKEND_LOGLEVEL", "INFO").upper()
logging.basicConfig(level=LOG_LEVEL, format="[%(asctime)s] %(levelname)s %(message)s")
log = logging.getLogger("ai_backend")

# -----------------------
# Job store
# -----------------------
_jobs: Dict[str, Dict[str, Any]] = {}
_executor = ThreadPoolExecutor(max_workers=1)  # 1 job at a time (GPU-safe)
_svd_pipe = None  # lazy pipeline cache


def _now() -> float:
    return time.time()


def _append_job_log(job: Dict[str, Any], msg: str) -> None:
    job["updated_at"] = _now()
    job.setdefault("log", [])
    job["log"].append({"ts": job["updated_at"], "msg": msg})
    # keep last 300 lines
    if len(job["log"]) > 300:
        job["log"] = job["log"][-300:]


# -----------------------
# Path helpers (Win <-> WSL)
# -----------------------
_drive_re = re.compile(r"^([A-Za-z]):[\\/](.*)$")


def win_to_wsl_path(p: str) -> str:
    """Convert Windows path like H:\\a\\b or H:/a/b to WSL /mnt/h/a/b.
    If already looks like /mnt/... or /home/... returns as-is.
    """
    if not p:
        return p
    p = p.strip()
    if p.startswith("/"):
        return p
    p2 = p.replace("\\", "/")
    m = _drive_re.match(p2)
    if not m:
        return p2
    drive = m.group(1).lower()
    rest = m.group(2)
    return f"/mnt/{drive}/{rest}"


def wsl_to_win_path(p: str) -> str:
    """Convert WSL path /mnt/h/a/b -> H:\\a\\b. Otherwise return as-is."""
    if not p:
        return p
    p = p.strip()
    m = re.match(r"^/mnt/([a-zA-Z])/(.*)$", p)
    if not m:
        return p
    drive = m.group(1).upper()
    rest = m.group(2).replace("/", "\\")
    return f"{drive}:\\{rest}"


def resolve_maybe_relative(path_str: str, base_dir: str) -> str:
    """If path is relative, resolve from base_dir."""
    if not path_str:
        return path_str
    # windows relative like "icons/a.png" also counts
    if path_str.startswith("/") or re.match(r"^[A-Za-z]:[\\/]", path_str):
        return path_str
    return os.path.abspath(os.path.join(base_dir, path_str))


# -----------------------
# API models
# -----------------------
class RenderRequest(BaseModel):
    shapes_json: str = Field(..., description="Path to shapes.json (Windows or WSL path)")
    out_mp4: str = Field(..., description="Output mp4 path (Windows or WSL path)")
    masks_dir: Optional[str] = Field(None, description="Optional (not used by this backend version)")
    pieces_dir: Optional[str] = Field(None, description="Optional (not used by this backend version)")
    fps: int = 7
    num_frames: int = 25
    pad: int = 32
    feather_px: int = 5
    seed_base: int = 123
    render_mode: str = Field("final", description="Quality preset: preview|final")
    layer_render: bool = Field(True, description="Render per tool/settings layer (faster, fewer seams)")
    enable_cache: bool = Field(True, description="Cache generated layer frames for reuse")


# -----------------------
# Core SVD render (no Qt, pure PIL/numpy)
# -----------------------
def _load_svd_pipeline(device: str = "cuda"):
    """Lazy load StableVideoDiffusionPipeline once per backend process."""
    global _svd_pipe
    if _svd_pipe is not None:
        return _svd_pipe

    import torch
    from diffusers import StableVideoDiffusionPipeline

    dtype = torch.float16 if device.startswith("cuda") else torch.float32
    pipe = StableVideoDiffusionPipeline.from_pretrained(
        "stabilityai/stable-video-diffusion-img2vid-xt",
        torch_dtype=dtype,
        variant="fp16" if dtype == torch.float16 else None,
    )
    if device.startswith("cuda"):
        pipe.to(device)
        try:
            pipe.enable_xformers_memory_efficient_attention()
        except Exception:
            pass
    else:
        pipe.to("cpu")

    # offload if available
    try:
        pipe.enable_model_cpu_offload()
    except Exception:
        pass

    _svd_pipe = pipe
    return pipe


def _round_to_multiple(x: int, m: int = 64) -> int:
    import math
    return int(math.ceil(x / m) * m)


def _make_shape_mask(shape: Dict[str, Any], size_wh: tuple[int, int], feather_px: int = 5):
    """Return PIL L mask for shape (full canvas). Supports Rectangle/Circle/Polygon."""
    from PIL import Image, ImageDraw, ImageFilter

    W, H = size_wh
    mask = Image.new("L", (W, H), 0)
    d = ImageDraw.Draw(mask)

    t = str(shape.get("type", "")).lower()
    if t == "polygon":
        pts = shape.get("points") or []
        poly = [(int(p["x"]), int(p["y"])) for p in pts if "x" in p and "y" in p]
        if len(poly) >= 3:
            d.polygon(poly, fill=255)
    else:
        x = int(shape.get("x", 0))
        y = int(shape.get("y", 0))
        w = int(shape.get("width", 0))
        h = int(shape.get("height", 0))
        box = [x, y, x + w, y + h]
        if t == "circle":
            d.ellipse(box, fill=255)
        else:  # rectangle / unknown -> rectangle
            d.rectangle(box, fill=255)

    if feather_px and feather_px > 0:
        mask = mask.filter(ImageFilter.GaussianBlur(radius=feather_px))
    return mask


def _crop_with_padding(bg, mask_full, shape: Dict[str, Any], pad: int = 32):
    """Crop region around shape bbox + padding. Returns (crop_rgb, mask_crop_L, (x0,y0,x1,y1), offx, offy)."""
    from PIL import Image

    W, H = bg.size
    t = str(shape.get("type", "")).lower()
    if t == "polygon":
        pts = shape.get("points") or []
        xs = [int(p["x"]) for p in pts if "x" in p]
        ys = [int(p["y"]) for p in pts if "y" in p]
        if not xs or not ys:
            x = y = 0
            w = h = 0
        else:
            x0b, y0b, x1b, y1b = min(xs), min(ys), max(xs), max(ys)
            x, y, w, h = x0b, y0b, (x1b - x0b), (y1b - y0b)
    else:
        x = int(shape.get("x", 0))
        y = int(shape.get("y", 0))
        w = int(shape.get("width", 0))
        h = int(shape.get("height", 0))

    x0 = max(0, x - pad)
    y0 = max(0, y - pad)
    x1 = min(W, x + w + pad)
    y1 = min(H, y + h + pad)

    crop = bg.crop((x0, y0, x1, y1)).convert("RGB")
    mask_crop = mask_full.crop((x0, y0, x1, y1)).convert("L")
    offx, offy = x - x0, y - y0
    return crop, mask_crop, (x0, y0, x1, y1), offx, offy


def _alpha_blend(dst_rgba_np, src_rgb_pil, alpha_mask_L_pil, top_left_xy):
    """Overlay src_rgb onto dst_rgba using alpha mask at position.
    Robust to size mismatches and out-of-bounds placement.
    """
    import numpy as np
    x0, y0 = map(int, top_left_xy)
    dst_h, dst_w = dst_rgba_np.shape[:2]

    src_pil = src_rgb_pil.convert("RGB")
    a_pil = alpha_mask_L_pil.convert("L")

    a = np.array(a_pil, dtype=np.float32) / 255.0
    h, w = a.shape

    if src_pil.size != (w, h):
        src_pil = src_pil.resize((w, h))
    src = np.array(src_pil, dtype=np.float32)

    dx0 = max(0, x0)
    dy0 = max(0, y0)
    dx1 = min(dst_w, x0 + w)
    dy1 = min(dst_h, y0 + h)
    if dx1 <= dx0 or dy1 <= dy0:
        return dst_rgba_np

    sx0 = dx0 - x0
    sy0 = dy0 - y0
    ow = dx1 - dx0
    oh = dy1 - dy0

    src_crop = src[sy0:sy0 + oh, sx0:sx0 + ow, :]
    a_crop = a[sy0:sy0 + oh, sx0:sx0 + ow][..., None]

    roi = dst_rgba_np[dy0:dy0 + oh, dx0:dx0 + ow, :].astype(np.float32)
    roi[..., :3] = src_crop * a_crop + roi[..., :3] * (1.0 - a_crop)
    roi[..., 3] = 255
    dst_rgba_np[dy0:dy0 + oh, dx0:dx0 + ow, :] = roi.astype(np.uint8)
    return dst_rgba_np



def _svd_generate_frames(
    pipe,
    pil_image_rgb,
    fps: int,
    num_frames: int,
    seed: int,
    motion_bucket_id: int = 127,
    noise_aug_strength: float = 0.02,
    decode_chunk_size: int = 2,
):
    """Generate frames with SVD for a single input image.

    Some SVD pipelines output a fixed resolution regardless of input.
    We always resize frames back to the original input size so masks align.
    """
    import torch
    import numpy as np
    gen_device = "cuda" if torch.cuda.is_available() else "cpu"
    generator = torch.Generator(device=gen_device).manual_seed(int(seed))

    from PIL import Image

    w, h = pil_image_rgb.size
    w2, h2 = _round_to_multiple(w, 64), _round_to_multiple(h, 64)

    # IMPORTANT: do not rescale (causes seams/warping). Pad instead.
    if (w2, h2) != (w, h):
        # Fill pad area with the mean edge color (better than black).
        arr = np.array(pil_image_rgb, dtype=np.uint8)
        edge = np.concatenate([
            arr[0:1, :, :],
            arr[-1:, :, :],
            arr[:, 0:1, :],
            arr[:, -1:, :],
        ], axis=0)
        fill = tuple(int(x) for x in edge.reshape(-1, 3).mean(axis=0))
        img = Image.new("RGB", (w2, h2), fill)
        img.paste(pil_image_rgb, (0, 0))
    else:
        img = pil_image_rgb

    out = pipe(
        img,
        num_frames=num_frames,
        fps=fps,
        generator=generator,
        motion_bucket_id=int(motion_bucket_id),
        noise_aug_strength=float(noise_aug_strength),
        decode_chunk_size=int(decode_chunk_size),
    )
    frames = out.frames[0]

    # crop away padding
    if frames and frames[0].size != (w, h):
        frames = [f.crop((0, 0, w, h)) for f in frames]
    return frames


def _card_to_svd_settings(card: Optional[Dict[str, Any]]):
    """Map UI shape_cards to SVD settings (motion/noise) + alpha scaling."""
    motion_bucket_id = 127
    noise_aug_strength = 0.02
    alpha_scale = 0.75

    if not card:
        return motion_bucket_id, noise_aug_strength, alpha_scale

    main = card.get("main") or {}
    params = main.get("params") or {}
    intensity = str(params.get("intensity", "normal")).lower()
    randomness = str(params.get("randomness", "normal")).lower()
    opacity = str(params.get("opacity", "normal")).lower()

    # NOTE: slightly more conservative defaults => less flicker/darkening on most assets.
    motion_bucket_id = {"weak": 80, "normal": 96, "strong": 127}.get(intensity, 96)
    noise_aug_strength = {"weak": 0.008, "normal": 0.015, "strong": 0.03}.get(randomness, 0.015)
    alpha_scale = {"weak": 0.55, "normal": 0.75, "strong": 1.0}.get(opacity, 0.75)
    return motion_bucket_id, noise_aug_strength, alpha_scale


def _shape_bbox(sh: Dict[str, Any]) -> Optional[tuple[int, int, int, int]]:
    """Return (x, y, w, h) for the shape, supporting polygons."""
    try:
        t = str(sh.get("type", "")).lower()
        if t == "polygon":
            pts = sh.get("points") or []
            xs = [int(p["x"]) for p in pts if "x" in p]
            ys = [int(p["y"]) for p in pts if "y" in p]
            if not xs or not ys:
                return None
            x0b, y0b, x1b, y1b = min(xs), min(ys), max(xs), max(ys)
            w = max(0, x1b - x0b)
            h = max(0, y1b - y0b)
            return (x0b, y0b, w, h)
        x = int(sh.get("x", 0))
        y = int(sh.get("y", 0))
        w = int(sh.get("width", 0))
        h = int(sh.get("height", 0))
        if w <= 0 or h <= 0:
            return None
        return (x, y, w, h)
    except Exception:
        return None


def _mask_shrink_and_feather(mask_L, *, shrink_px: int, feather_px: int):
    """Shrink mask a little (reduce edge halos), then feather."""
    from PIL import ImageFilter

    m = mask_L.convert("L")
    if shrink_px and shrink_px > 0:
        # MinFilter acts like erosion for white-on-black masks.
        # size must be odd; 3 ~ 1px, 5 ~ 2px.
        size = 2 * int(shrink_px) + 1
        size = max(3, size | 1)
        m = m.filter(ImageFilter.MinFilter(size=size))
    if feather_px and feather_px > 0:
        m = m.filter(ImageFilter.GaussianBlur(radius=float(feather_px)))
    return m


def _prepare_focus_patch(patch_rgb, mask_hard_L, *, blur_outside_px: int = 8):
    """Blur everything OUTSIDE mask so SVD focuses on the region."""
    from PIL import ImageFilter

    blur = patch_rgb.filter(ImageFilter.GaussianBlur(radius=float(blur_outside_px)))
    # composite: inside mask -> original, outside -> blur
    return Image.composite(patch_rgb, blur, mask_hard_L.convert("L"))


def _color_match_frame(frame_rgb, ref_rgb, mask_L, *, max_shift: int = 20):
    """Match mean RGB inside mask to reduce brightness/color drift."""
    import numpy as np

    fr = np.array(frame_rgb.convert("RGB"), dtype=np.int16)
    rr = np.array(ref_rgb.convert("RGB"), dtype=np.int16)
    m = np.array(mask_L.convert("L"), dtype=np.uint8)
    idx = m > 16
    if idx.sum() < 64:
        return frame_rgb

    # means inside mask
    fr_m = fr[idx].mean(axis=0)
    rr_m = rr[idx].mean(axis=0)
    shift = np.clip(rr_m - fr_m, -max_shift, max_shift).astype(np.int16)
    fr2 = np.clip(fr + shift[None, None, :], 0, 255).astype(np.uint8)
    return Image.fromarray(fr2, mode="RGB")


def _temporal_smooth_frames(frames_rgb, mask_L, *, strength: float = 0.15):
    """Simple EMA smoothing inside mask to reduce flicker."""
    import numpy as np

    if not frames_rgb:
        return frames_rgb
    m = np.array(mask_L.convert("L"), dtype=np.float32) / 255.0
    if m.max() < 1e-3:
        return frames_rgb

    prev = np.array(frames_rgb[0].convert("RGB"), dtype=np.float32)
    out = [frames_rgb[0]]
    w = (strength * m)[..., None]
    for f in frames_rgb[1:]:
        cur = np.array(f.convert("RGB"), dtype=np.float32)
        sm = cur * (1.0 - w) + prev * w
        sm_u8 = np.clip(sm, 0, 255).astype(np.uint8)
        img = Image.fromarray(sm_u8, mode="RGB")
        out.append(img)
        prev = sm
    return out


def _cache_path(base_dir: str, key: str) -> str:
    d = os.path.join(base_dir, "cache", "svd_layers")
    os.makedirs(d, exist_ok=True)
    return os.path.join(d, f"{key}.npz")


def _make_cache_key(*, patch_rgb, mask_L, settings: Dict[str, Any]) -> str:
    h = hashlib.sha256()
    h.update(str(patch_rgb.size).encode("utf-8"))
    h.update(patch_rgb.tobytes())
    h.update(str(mask_L.size).encode("utf-8"))
    h.update(mask_L.tobytes())
    h.update(json.dumps(settings, sort_keys=True).encode("utf-8"))
    return h.hexdigest()[:32]


def _save_cached_frames(path: str, frames_rgb) -> None:
    import numpy as np
    arr = np.stack([np.array(f.convert("RGB"), dtype=np.uint8) for f in frames_rgb], axis=0)
    np.savez_compressed(path, frames=arr)


def _load_cached_frames(path: str):
    import numpy as np
    from PIL import Image
    z = np.load(path)
    arr = z["frames"]
    return [Image.fromarray(arr[i], mode="RGB") for i in range(arr.shape[0])]



def _render_svd_job(job_id: str, req: RenderRequest) -> None:
    """Main render routine executed in a background thread.

    Pipeline:
      - Read shapes.json
      - Choose base background: without_shape_area.png (preferred) or shapes.json["background"]
      - For each shape:
          * If pieces/shape_<id>.png exists -> use it (alpha is mask) and paste into crop for conditioning
          * Else fallback to geometry mask from shapes.json
      - Run SVD per-shape to generate animated patch frames
      - Alpha-blend patches back to base frames
      - Encode mp4
    """
    job = _jobs[job_id]
    _append_job_log(job, "job started")

    # --- resolve paths (Win -> WSL) ---
    shapes_json_wsl = win_to_wsl_path(req.shapes_json)
    out_mp4_wsl = win_to_wsl_path(req.out_mp4)
    out_dir = os.path.dirname(out_mp4_wsl) or "."
    os.makedirs(out_dir, exist_ok=True)

    job["paths"] = {
        "shapes_json_win": req.shapes_json,
        "out_mp4_win": req.out_mp4,
        "shapes_json_wsl": shapes_json_wsl,
        "out_mp4_wsl": out_mp4_wsl,
    }
    _append_job_log(job, f"paths resolved: {job['paths']}")

    # --- load shapes.json ---
    if not os.path.exists(shapes_json_wsl):
        raise RuntimeError(f"shapes.json not found: {shapes_json_wsl}")

    base_dir = os.path.dirname(shapes_json_wsl)
    with open(shapes_json_wsl, "r", encoding="utf-8") as f:
        data = json.load(f)

    shapes = data.get("shapes") or []
    if not shapes:
        raise RuntimeError("shapes.json: empty shapes list")

    # --- per-shape UI settings (optional) ---
    shape_cards = data.get("shape_cards") or []
    cards_by_id: Dict[int, Dict[str, Any]] = {}
    for c in shape_cards:
        try:
            cid = int(c.get("id"))
        except Exception:
            continue
        cards_by_id[cid] = c

    # --- quality preset ---
    mode = str(req.render_mode or "final").lower().strip()
    is_preview = mode.startswith("pre")
    fps = int(req.fps)
    num_frames = int(req.num_frames)
    if is_preview:
        # if user kept defaults, use a faster preview preset
        if fps == 7:
            fps = 6
        if num_frames == 25:
            num_frames = 14
    pad_eff = max(int(req.pad), 48 if is_preview else 64)
    feather_eff = int(req.feather_px)
    shrink_px = 1 if is_preview else 2
    blur_outside_px = 6 if is_preview else 8
    decode_chunk_size = 4 if is_preview else 2
    temporal_strength = 0.12 if is_preview else 0.15

    _append_job_log(job, f"preset: mode={mode} fps={fps} frames={num_frames} pad={pad_eff}")

    # --- choose background (conditioning uses original, base uses without_shape if available) ---
    without_wsl = os.path.join(base_dir, "without_shape_area.png")
    bg_path_raw = data.get("background", "")
    bg_path_resolved = resolve_maybe_relative(bg_path_raw, base_dir)
    bg_path_wsl = win_to_wsl_path(bg_path_resolved)
    if not os.path.exists(bg_path_wsl):
        raise RuntimeError(f"background image not found: {bg_path_wsl} (from {bg_path_raw})")

    # --- pieces dir (optional) ---
    pieces_dir_raw = req.pieces_dir or os.path.join(base_dir, "pieces")
    pieces_dir_resolved = resolve_maybe_relative(pieces_dir_raw, base_dir)
    pieces_dir_wsl = win_to_wsl_path(pieces_dir_resolved)
    if not os.path.isdir(pieces_dir_wsl):
        pieces_dir_wsl = ""

    # --- init SVD pipeline and base frames ---
    job["state"] = "running"
    job["progress"] = {"stage": "loading_pipeline", "current": 0, "total": len(shapes)}
    _append_job_log(job, "loading SVD pipeline (first time may take long)")

    import torch
    device = "cuda" if torch.cuda.is_available() else "cpu"
    pipe = _load_svd_pipeline(device=device)

    from PIL import Image, ImageFilter
    import numpy as np

    bg_orig = Image.open(bg_path_wsl).convert("RGB")
    W, H = bg_orig.size

    base_bg = bg_orig.copy()
    if os.path.exists(without_wsl):
        try:
            wimg = Image.open(without_wsl)
            if wimg.size == bg_orig.size:
                if wimg.mode in ("RGBA", "LA") or ("transparency" in getattr(wimg, "info", {})):
                    base_bg = Image.alpha_composite(bg_orig.convert("RGBA"), wimg.convert("RGBA")).convert("RGB")
                else:
                    base_bg = wimg.convert("RGB")
        except Exception:
            # fallback: ignore without_shape
            base_bg = bg_orig.copy()

    base_np = np.array(base_bg, dtype=np.uint8)
    rgba0 = np.dstack([base_np, np.full((H, W), 255, dtype=np.uint8)])
    base_frames = [rgba0.copy() for _ in range(num_frames)]

    # --- group shapes into layers (stage2) ---
    layers: Dict[tuple[str, int, float], list[tuple[Dict[str, Any], int, float]]] = {}
    for idx, sh in enumerate(shapes, start=1):
        try:
            sid = int(sh.get("id") or idx)
        except Exception:
            sid = idx

        card = cards_by_id.get(sid) or {}
        tool = str(card.get("tool_type") or "default").lower()
        motion_bucket_id, noise_aug_strength, alpha_scale = _card_to_svd_settings(card)

        key = (tool, int(motion_bucket_id), float(noise_aug_strength))
        layers.setdefault(key, []).append((sh, sid, float(alpha_scale)))

    layer_items = list(layers.items())
    total_layers = len(layer_items)
    _append_job_log(job, f"layers: {total_layers} (layer_render={req.layer_render})")

    from PIL import ImageDraw, ImageChops

    def _render_one_layer(layer_idx: int, layer_key, entries):
        tool, motion_bucket_id, noise_aug_strength = layer_key

        # union bbox
        boxes = []
        for sh, sid, _a in entries:
            bb = _shape_bbox(sh)
            if bb:
                boxes.append(bb)
        if not boxes:
            _append_job_log(job, f"skip layer {tool}: no valid bboxes")
            return

        x_min = min(b[0] for b in boxes)
        y_min = min(b[1] for b in boxes)
        x_max = max(b[0] + b[2] for b in boxes)
        y_max = max(b[1] + b[3] for b in boxes)

        x0 = max(0, x_min - pad_eff)
        y0 = max(0, y_min - pad_eff)
        x1 = min(W, x_max + pad_eff)
        y1 = min(H, y_max + pad_eff)
        if x1 <= x0 or y1 <= y0:
            _append_job_log(job, f"skip layer {tool}: invalid crop")
            return

        pw, ph = (x1 - x0), (y1 - y0)
        # If the union becomes too large, fall back to per-shape to keep speed reasonable.
        if len(entries) > 1 and pw * ph > 1024 * 1024:
            _append_job_log(job, f"layer {tool} too large ({pw}x{ph}); falling back to per-shape")
            for sh, sid, a in entries:
                _render_one_layer(layer_idx, (tool, motion_bucket_id, noise_aug_strength), [(sh, sid, a)])
            return

        patch_bg = bg_orig.crop((x0, y0, x1, y1)).convert("RGB")
        patch = patch_bg.copy()

        mask_hard = Image.new("L", (pw, ph), 0)

        # Build patch (paste pieces) + union alpha mask
        for sh, sid, alpha_scale in entries:
            bb = _shape_bbox(sh)
            if not bb:
                continue
            x, y, w, h = bb
            offx, offy = x - x0, y - y0
            if w <= 0 or h <= 0:
                continue

            tmp = Image.new("L", (pw, ph), 0)

            piece_path = os.path.join(pieces_dir_wsl, f"shape_{sid}.png") if pieces_dir_wsl else ""
            if piece_path and os.path.exists(piece_path):
                piece_rgba = Image.open(piece_path).convert("RGBA")
                if piece_rgba.size != (w, h):
                    piece_rgba = piece_rgba.resize((w, h))
                a = piece_rgba.split()[-1].convert("L")
                patch.paste(piece_rgba.convert("RGB"), (offx, offy), mask=a)
                tmp.paste(a, (offx, offy))
            else:
                d = ImageDraw.Draw(tmp)
                t = str(sh.get("type", "")).lower()
                if t == "circle":
                    d.ellipse([offx, offy, offx + w, offy + h], fill=255)
                elif t == "polygon":
                    pts = sh.get("points") or []
                    poly = [(int(p["x"]) - x0, int(p["y"]) - y0) for p in pts if "x" in p and "y" in p]
                    if len(poly) >= 3:
                        d.polygon(poly, fill=255)
                else:
                    d.rectangle([offx, offy, offx + w, offy + h], fill=255)

            if alpha_scale != 1.0:
                a_np = (np.array(tmp, dtype=np.float32) * float(alpha_scale)).clip(0, 255).astype(np.uint8)
                tmp = Image.fromarray(a_np, mode="L")

            mask_hard = ImageChops.lighter(mask_hard, tmp)

        if mask_hard.getbbox() is None:
            _append_job_log(job, f"skip layer {tool}: empty mask")
            return

        # focus mask for conditioning / stabilization
        mask_focus = mask_hard.point(lambda p: 255 if p > 4 else 0)

        # final blend mask
        mask_final = _mask_shrink_and_feather(mask_hard, shrink_px=shrink_px, feather_px=feather_eff)

        patch_cond = _prepare_focus_patch(patch, mask_focus, blur_outside_px=blur_outside_px)

        seed = int(req.seed_base)  # unified seed across layers

        settings = {
            "tool": tool,
            "motion_bucket_id": int(motion_bucket_id),
            "noise_aug_strength": float(noise_aug_strength),
            "fps": int(fps),
            "num_frames": int(num_frames),
            "seed": seed,
            "decode_chunk_size": int(decode_chunk_size),
        }
        ckey = _make_cache_key(patch_rgb=patch_cond, mask_L=mask_focus, settings=settings)
        cpath = _cache_path(base_dir, ckey)

        if req.enable_cache and os.path.exists(cpath):
            _append_job_log(job, f"cache hit: layer {tool} -> {os.path.basename(cpath)}")
            frames_piece = _load_cached_frames(cpath)
        else:
            _append_job_log(job, f"SVD layer {tool}: motion={motion_bucket_id} noise={noise_aug_strength:.3f}")
            frames_piece = _svd_generate_frames(
                pipe,
                patch_cond,
                fps=fps,
                num_frames=num_frames,
                seed=seed,
                motion_bucket_id=int(motion_bucket_id),
                noise_aug_strength=float(noise_aug_strength),
                decode_chunk_size=decode_chunk_size,
            )

            # post: reduce drift/flicker
            frames_piece = [_color_match_frame(f, patch, mask_focus) for f in frames_piece]
            frames_piece = _temporal_smooth_frames(frames_piece, mask_focus, strength=temporal_strength)

            if req.enable_cache:
                try:
                    _save_cached_frames(cpath, frames_piece)
                except Exception:
                    pass

        # blend back
        for t_idx in range(num_frames):
            base_frames[t_idx] = _alpha_blend(base_frames[t_idx], frames_piece[t_idx], mask_final, (x0, y0))

    if req.layer_render:
        for li, (layer_key, entries) in enumerate(layer_items, start=1):
            job["progress"] = {"stage": "rendering", "current": li, "total": total_layers, "layer": str(layer_key)}
            _append_job_log(job, f"rendering layer {li}/{total_layers}: {layer_key}")
            _render_one_layer(li, layer_key, entries)
    else:
        # fallback (legacy): treat each shape as its own layer, but keep stabilization improvements.
        flat = []
        for k, entries in layer_items:
            for sh, sid, a in entries:
                flat.append((("shape",) + k[1:], [(sh, sid, a)]))
        for li, (layer_key, entries) in enumerate(flat, start=1):
            job["progress"] = {"stage": "rendering", "current": li, "total": len(flat), "layer": str(layer_key)}
            _render_one_layer(li, layer_key, entries)

    # --- encode ---
    job["progress"] = {"stage": "encoding", "current": total_layers, "total": total_layers}
    _append_job_log(job, "encoding mp4")

    import imageio
    writer = imageio.get_writer(
        out_mp4_wsl, fps=fps, format="FFMPEG", codec="libx264", pixelformat="yuv420p"
    )
    for t_idx in range(num_frames):
        writer.append_data(base_frames[t_idx][..., :3])
    writer.close()

    job["state"] = "done"
    job["result"] = {"out_mp4_wsl": out_mp4_wsl, "out_mp4_win": wsl_to_win_path(out_mp4_wsl)}
    job["progress"] = {"stage": "done", "current": total_layers, "total": total_layers}
    _append_job_log(job, f"done: {job['result']}")


# -----------------------
# Middleware: log requests
# -----------------------
@app.middleware("http")
async def log_requests(request: Request, call_next):
    rid = uuid.uuid4().hex[:8]
    start = _now()
    try:
        response = await call_next(request)
        dur = (_now() - start) * 1000.0
        log.info("[%s] %s %s -> %s (%.1fms)", rid, request.method, request.url.path, response.status_code, dur)
        return response
    except Exception as e:
        dur = (_now() - start) * 1000.0
        log.exception("[%s] %s %s !! %s (%.1fms)", rid, request.method, request.url.path, e, dur)
        raise


# -----------------------
# Routes
# -----------------------
@app.get("/")
def root():
    return {
        "service": "ai_editor backend",
        "ok": True,
        "health": "/health",
        "gpu": "/gpu",
        "render": "/svd/render",
    }


@app.get("/health")
def health():
    return {
        "ok": True,
        "service": "ai_editor backend",
        "version": app.version,
        "ts": _now(),
    }


@app.get("/gpu")
def gpu():
    try:
        import torch
        cuda = torch.cuda.is_available()
        dev = torch.cuda.get_device_name(0) if cuda else None
        return {"cuda_available": cuda, "device": dev, "torch": torch.__version__}
    except Exception as e:
        return {"cuda_available": False, "device": None, "error": str(e)}


@app.post("/svd/render")
def svd_render(req: RenderRequest, request: Request):
    job_id = uuid.uuid4().hex
    job = {
        "job_id": job_id,
        "state": "queued",
        "created_at": _now(),
        "updated_at": _now(),
        "payload": req.model_dump(),
        "client": {"host": request.client.host if request.client else None},
        "progress": {"stage": "queued", "current": 0, "total": 0},
        "log": [],
    }
    _jobs[job_id] = job
    _append_job_log(job, "queued")

    # run async in executor
    def _runner():
        try:
            _render_svd_job(job_id, req)
        except Exception as e:
            job["state"] = "error"
            job["error"] = str(e)
            _append_job_log(job, f"ERROR: {e}")
            log.exception("Job %s failed: %s", job_id, e)

    _executor.submit(_runner)
    return {"job_id": job_id}


@app.get("/svd/status/{job_id}")
def svd_status(job_id: str):
    job = _jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="job_id not found")
    # return a safe copy
    return job
