import json
import math

import cv2
import imageio
import numpy as np
# ---- SVD ----
import torch
from PIL import Image, ImageDraw, ImageFilter
from diffusers import StableVideoDiffusionPipeline


def round_to_multiple(x, m=64):
    return int(math.ceil(x / m) * m)


def make_shape_mask(shape, size_wh, feather_px=5):
    """Full-size mask for the whole background."""
    W, H = size_wh
    m = Image.new("L", (W, H), 0)
    d = ImageDraw.Draw(m)

    x, y = int(shape["x"]), int(shape["y"])
    w, h = int(shape["width"]), int(shape["height"])

    if shape["type"].lower() == "circle":
        d.ellipse([x, y, x + w, y + h], fill=255)
    else:  # Rectangle
        d.rectangle([x, y, x + w, y + h], fill=255)

    if feather_px and feather_px > 0:
        m = m.filter(ImageFilter.GaussianBlur(radius=feather_px))
    return m


def crop_with_padding(img, mask_full, shape, pad=64):
    """Crop a region around shape + padding, also returns cropped mask and crop box."""
    W, H = img.size
    x, y = int(shape["x"]), int(shape["y"])
    w, h = int(shape["width"]), int(shape["height"])

    x0 = max(0, x - pad)
    y0 = max(0, y - pad)
    x1 = min(W, x + w + pad)
    y1 = min(H, y + h + pad)

    crop = img.crop((x0, y0, x1, y1))
    mask = mask_full.crop((x0, y0, x1, y1))
    return crop, mask, (x0, y0, x1, y1)


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

        # экономия памяти, если доступно
        try:
            self.pipe.enable_model_cpu_offload()
        except Exception:
            pass

    @torch.inference_mode()
    def generate_frames(self, pil_image_rgb, fps=7, num_frames=25,
                        seed=42, motion_bucket_id=127, noise_aug_strength=0.02,
                        decode_chunk_size=2):
        # SVD любит размеры кратные 64; приводим кроп к ближайшим
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
        frames = out.frames[0]  # list[PIL]
        # вернем к исходному размеру кропа
        frames = [f.resize((w, h), Image.LANCZOS) for f in frames]
        return frames


def alpha_blend(dst_rgba, src_rgb, alpha_mask_L, top_left_xy):
    """Overlay src_rgb onto dst_rgba using alpha_mask_L at position top_left_xy."""
    x0, y0 = top_left_xy
    src = np.array(src_rgb.convert("RGB"), dtype=np.uint8)
    a = np.array(alpha_mask_L, dtype=np.uint8)  # 0..255

    h, w = a.shape
    dst = dst_rgba

    roi = dst[y0:y0 + h, x0:x0 + w, :].astype(np.float32)
    src_f = src.astype(np.float32)

    a_f = (a.astype(np.float32) / 255.0)[..., None]  # HxWx1
    roi[..., :3] = src_f * a_f + roi[..., :3] * (1.0 - a_f)
    roi[..., 3] = np.clip(roi[..., 3] + a, 0, 255)  # можно и просто 255, если фон непрозрачный

    dst[y0:y0 + h, x0:x0 + w, :] = roi.astype(np.uint8)
    return dst


def main(shapes_json_path, out_mp4="result.mp4",
         fps=7, num_frames=25,
         pad=64, feather_px=5,
         seed_base=123):
    with open(shapes_json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    bg_path = data["background"]  # путь как в твоем json :contentReference[oaicite:1]{index=1}
    shapes = data["shapes"]

    bg = Image.open(bg_path).convert("RGB")
    W, H = bg.size

    # базовые кадры (фон статичный)
    base_frames = []
    for _ in range(num_frames):
        rgba = np.dstack([np.array(bg, dtype=np.uint8), np.full((H, W), 255, dtype=np.uint8)])
        base_frames.append(rgba)

    svd = SVDImg2Vid(device="cuda")  # или "cpu"

    # порядок наложения = порядок shapes (можешь заменить на z-index)
    for idx, sh in enumerate(shapes):
        mask_full = make_shape_mask(sh, (W, H), feather_px=feather_px)

        crop, mask_crop, (x0, y0, x1, y1) = crop_with_padding(bg, mask_full, sh, pad=pad)

        # Генерим анимацию для этого кропа
        frames_piece = svd.generate_frames(
            crop,
            fps=fps,
            num_frames=num_frames,
            seed=seed_base + int(sh["id"]) * 100,
            motion_bucket_id=127,
            noise_aug_strength=0.02
        )

        # Композитим каждый кадр обратно
        for t in range(num_frames):
            base_frames[t] = alpha_blend(
                base_frames[t],
                frames_piece[t],
                mask_crop,
                (x0, y0)
            )

    # export mp4
    writer = imageio.get_writer(out_mp4, fps=fps, codec="libx264", quality=8)
    for t in range(num_frames):
        frame_rgb = base_frames[t][..., :3]
        writer.append_data(frame_rgb)
    writer.close()

    print("Saved:", out_mp4)


if __name__ == "__main__":
    main("shapes.json", out_mp4="result.mp4")
