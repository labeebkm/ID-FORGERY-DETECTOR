from dataclasses import dataclass

import cv2
import numpy as np

from backend.utils import encode_png_base64, pil_to_numpy_bgr


@dataclass
class EdgeResult:
    has_artifacts: bool
    score: float       # 0–1
    edge_map_b64: str


def run_edge_detection(pil_image) -> EdgeResult:
    """
    Canny edge detection with heuristic scoring.
    Forged regions often show unusually sharp or concentrated edge patterns.
    """
    bgr = pil_to_numpy_bgr(pil_image)
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)

    edges = cv2.Canny(gray, threshold1=80, threshold2=160)

    h, w = edges.shape
    edge_pixels = float((edges > 0).sum())
    total_pixels = float(h * w) if h > 0 and w > 0 else 1.0
    density = edge_pixels / total_pixels

    kernel = np.ones((5, 5), np.uint8)
    dilated = cv2.dilate(edges, kernel, iterations=1)
    hotspot = float(dilated.max()) / 255.0

    density_score = max(0.0, min(1.0, (density - 0.02) / 0.18))
    score = float(np.clip(0.6 * density_score + 0.4 * hotspot, 0.0, 1.0))

    # Cyan edges on dark background for visualization
    edge_vis = np.zeros_like(bgr)
    edge_vis[edges > 0] = (255, 255, 0)  # BGR: cyan

    edge_b64 = encode_png_base64(edge_vis)
    return EdgeResult(has_artifacts=score > 0.45, score=score, edge_map_b64=edge_b64)
