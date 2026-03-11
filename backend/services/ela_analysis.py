from dataclasses import dataclass
from io import BytesIO

import numpy as np
from PIL import Image

from backend.utils import encode_png_base64


@dataclass
class ElaResult:
    score: float        # normalized 0–1 suspicion score
    heatmap_b64: str    # base64 PNG data URL of the ELA heatmap


def run_ela_analysis(img: Image.Image, jpeg_quality: int = 75) -> ElaResult:
    """
    Error Level Analysis (ELA).

    Re-saves the image at a fixed JPEG quality, then measures per-pixel
    differences. Regions with a different compression history (i.e. previously
    edited/resaved areas) will show elevated error levels.
    """
    if img.mode != "RGB":
        img = img.convert("RGB")

    original = np.asarray(img).astype("float32")

    # Re-compress entirely in-memory
    buffer = BytesIO()
    img.save(buffer, format="JPEG", quality=jpeg_quality)
    buffer.seek(0)
    recompressed_np = np.asarray(
        Image.open(buffer).convert("RGB")
    ).astype("float32")

    # Per-pixel absolute difference, collapsed to grayscale brightness
    diff = np.abs(original - recompressed_np)
    brightness = diff.mean(axis=2)

    # Normalize to [0, 1] using the 99th percentile to avoid outlier saturation
    max_val = float(np.percentile(brightness, 99)) or 1.0
    norm = np.clip(brightness / max_val, 0.0, 1.0)

    mean_b = float(norm.mean())
    std_b = float(norm.std())
    score = float(np.clip(0.7 * mean_b + 0.3 * std_b, 0.0, 1.0))

    # Heatmap: blue → green → red (cool-to-warm) via manual colormap
    heat = (norm * 255.0).astype("uint8")
    # Red channel increases with error, blue decreases — gives a heat look
    r = heat
    g = (heat * 0.6).astype("uint8")
    b = (255 - heat).astype("uint8")
    heat_rgb = np.stack([r, g, b], axis=2)  # RGB order for encode_png_base64

    import cv2
    heat_bgr = cv2.cvtColor(heat_rgb, cv2.COLOR_RGB2BGR)
    heatmap_b64 = encode_png_base64(heat_bgr)

    return ElaResult(score=score, heatmap_b64=heatmap_b64)
