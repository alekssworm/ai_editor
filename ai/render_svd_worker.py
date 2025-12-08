import json
import math
import os

import imageio
import numpy as np
import torch
from PIL import Image
from diffusers import StableVideoDiffusionPipeline

from .svg_mask import rasterize_svg_to_mask


def round_to_multiple(x, m=64):
    return int(math.ceil(x / m) * m)


def crop_with_padding(img, x, y, w, h, pad=64):
    W, H = img.size
    x0 = max(0, x - pad)
    y0 = max(0, y - pad)
    x1 = min(W, x + w + pad)
    y1 = min(H, y + h + pad)
    return img.crop((x0, y0, x1, y1)), (x0, y0, x1, y1)


def alpha_blend(dst_rgba, src_rgb_pil, alpha_mask_L_pil, top_left_xy):
    x0, y0 = top_left_xy
    src = np.array(src_rgb_pil.convert("RGB"), dtype=np.uint8)
    a = np.array(alpha_mask_L_pil, dtype=np.uint8)  # HxW

    h, w = a.shape
    roi = dst_rgba[y0:y0 + h, x0:x0 + w, :].astype(np.float32)
    src_f = src.astype(np.float32)
    a_f = (a.astype(np.float32) / 255.0)[..., None]

    roi[..., :3] = src_f * a_f + roi[..., :3] * (1.0 - a_f)
    roi[..., 3] = 255  # фон у тебя обычно непрозрачный
    dst_rgba[y0:y0 + h, x0:x0 + w, :] = roi.astype(np.uint8)
    return dst_rgba


class SVDImg2Vid:
    def __init__(self, model_id="stabilityai/stable-video-diffusion-img2vid-xt", device="cuda"):
        self.device = device
        dtype = torch.float16 if device.startswith("cuda") else torch.float32

        self.pipe = StableVideoDiffusionPipeline.from_pretrained(
            model_id,
            torch_dtype=dtype,
            variant="fp16" if dtype == torch.float16 else None,
        )

        if device.startswith("cuda"):
            self.pipe.to(device)
            try:
                self.pipe.enable_xformers_memory_efficient_attention()
            except Exception:
                pass
        else:
            self.pipe.to("cpu")

        try:
            self.pipe.enable_model_cpu_offload()
        except Exception:
            pass

    @torch.inference_mode()
    def generate_frames(self, pil_image_rgb, fps=7, num_frames=25, seed=42,
                        motion_bucket_id=127, noise_aug_strength=0.02, decode_chunk_size=2):
        w, h = pil_image_rgb.size
        rw, rh = round_to_multiple(w, 64), round_to_multiple(h, 64)
        inp = pil_image_rgb.resize((rw, rh), Image.LANCZOS)

        g = torch.Generator(device=self.device if self.device.startswith("cuda") else "cpu").manual_seed(seed)

        out = self.pipe(
            inp,
            fps=fps,
            num_frames=num_frames,
            motion_bucket_id=motion_bucket_id,
            noise_aug_strength=noise_aug_strength,
            decode_chunk_size=decode_chunk_size,
            generator=g,
        )
        frames = out.frames[0]
        return [f.resize((w, h), Image.LANCZOS) for f in frames]


def render_from_shapes_json(shapes_json_path: str,
                            out_mp4: str,
                            masks_dir: str,
                            fps: int = 7,
                            num_frames: int = 25,
                            pad: int = 64,
                            feather_px: int = 5,
                            device: str = "cuda",
                            progress_cb=None):
    """
    shapes.json: background + shapes (x,y,w,h,id)
    masks_dir: папка с SVG масками, например masks/shape_1.svg
    """
    with open(shapes_json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    bg_path = data["background"]
    shapes = data["shapes"]

    bg = Image.open(bg_path).convert("RGB")
    W, H = bg.size

    base_frames = []
    for _ in range(num_frames):
        rgba = np.dstack([np.array(bg, dtype=np.uint8), np.full((H, W), 255, dtype=np.uint8)])
        base_frames.append(rgba)

    svd = SVDImg2Vid(device=device)

    total = len(shapes)
    for i, sh in enumerate(shapes, start=1):
        sid = int(sh["id"])
        x, y, w, h = int(sh["x"]), int(sh["y"]), int(sh["width"]), int(sh["height"])

        svg_path = os.path.join(masks_dir, f"shape_{sid}.svg")
        if not os.path.exists(svg_path):
            raise FileNotFoundError(f"SVG mask not found: {svg_path}")

        # 1) кроп фона вокруг shape
        crop_rgb, (x0, y0, x1, y1) = crop_with_padding(bg, x, y, w, h, pad=pad)
        cw, ch = crop_rgb.size

        # 2) полная SVG-маска в размере фона -> обрезаем под кроп
        mask_full = rasterize_svg_to_mask(svg_path, W, H, feather_px=feather_px)
        mask_crop = mask_full.crop((x0, y0, x1, y1))

        # 3) SVD на кропе
        frames_piece = svd.generate_frames(
            crop_rgb,
            fps=fps,
            num_frames=num_frames,
            seed=123 + sid * 100
        )

        # 4) вклейка обратно
        for t in range(num_frames):
            base_frames[t] = alpha_blend(base_frames[t], frames_piece[t], mask_crop, (x0, y0))

        if progress_cb:
            progress_cb(i, total, sid)

    writer = imageio.get_writer(out_mp4, fps=fps, codec="libx264", quality=8)
    for t in range(num_frames):
        writer.append_data(base_frames[t][..., :3])
    writer.close()

    return out_mp4
