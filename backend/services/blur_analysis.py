from dataclasses import dataclass

import cv2
import numpy as np

from backend.utils import pil_to_numpy_bgr


@dataclass
class BlurResult:
    has_inconsistency: bool
    score: float  # 0–1


def run_blur_analysis(pil_image) -> BlurResult:
    """
    Detect sharpness inconsistencies across image regions.
    Forged IDs often contain regions pasted from photos with different focus levels.
    """
    bgr = pil_to_numpy_bgr(pil_image)
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)

    h, w = gray.shape
    grid_y, grid_x = 4, 4
    patch_h = max(h // grid_y, 1)
    patch_w = max(w // grid_x, 1)

    sharpness_values = []
    for gy in range(grid_y):
        for gx in range(grid_x):
            y0 = gy * patch_h
            x0 = gx * patch_w
            y1 = h if gy == grid_y - 1 else (gy + 1) * patch_h
            x1 = w if gx == grid_x - 1 else (gx + 1) * patch_w
            patch = gray[y0:y1, x0:x1]
            if patch.size > 0:
                lap = cv2.Laplacian(patch, cv2.CV_64F)
                sharpness_values.append(float(lap.var()))

    if not sharpness_values:
        return BlurResult(has_inconsistency=False, score=0.0)

    values = np.array(sharpness_values, dtype="float32")
    mean_val = float(values.mean())
    std_val = float(values.std())

    cv = std_val / (mean_val + 1e-6)
    raw_score = (cv - 0.2) / (0.8 - 0.2)
    score = float(np.clip(raw_score, 0.0, 1.0))

    return BlurResult(has_inconsistency=score > 0.4, score=score)
