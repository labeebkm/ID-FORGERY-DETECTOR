from dataclasses import dataclass

import cv2
import numpy as np

from backend.utils import pil_to_numpy_bgr


@dataclass
class NoiseResult:
    anomaly: bool
    score: float  # 0–1


def run_noise_analysis(pil_image) -> NoiseResult:
    """
    Detect inconsistent noise across a spatial grid.
    Composited images often have different noise textures in different regions.
    """
    bgr = pil_to_numpy_bgr(pil_image)
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)

    blurred = cv2.GaussianBlur(gray, (7, 7), 0)
    noise = gray.astype("float32") - blurred.astype("float32")
    noise_sq = noise ** 2

    h, w = gray.shape
    grid_y, grid_x = 4, 4
    patch_h = max(h // grid_y, 1)
    patch_w = max(w // grid_x, 1)

    variances = []
    for gy in range(grid_y):
        for gx in range(grid_x):
            y0 = gy * patch_h
            x0 = gx * patch_w
            y1 = h if gy == grid_y - 1 else (gy + 1) * patch_h
            x1 = w if gx == grid_x - 1 else (gx + 1) * patch_w
            patch = noise_sq[y0:y1, x0:x1]
            if patch.size > 0:
                variances.append(float(patch.mean()))

    if not variances:
        return NoiseResult(anomaly=False, score=0.0)

    variances_np = np.array(variances, dtype="float32")
    mean_var = float(variances_np.mean())
    std_var = float(variances_np.std())

    cv = (std_var / mean_var) if mean_var > 0 else 0.0
    raw_score = (cv - 0.2) / (1.0 - 0.2)
    score = float(np.clip(raw_score, 0.0, 1.0))

    return NoiseResult(anomaly=score > 0.4, score=score)
