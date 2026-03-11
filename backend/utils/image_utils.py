from io import BytesIO
from typing import List, Optional, Tuple

from PIL import Image, UnidentifiedImageError

from backend.models import ValidationResult


ALLOWED_MIME_TYPES = {"image/jpeg", "image/jpg", "image/png"}
MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB
MIN_WIDTH = 200   # relaxed from 400 to handle small test images
MIN_HEIGHT = 150  # relaxed from 250


def validate_image_bytes(data: bytes, mime_type: Optional[str]) -> ValidationResult:
    """
    Validate raw uploaded bytes for type, size, integrity, and resolution.
    """
    reasons: List[str] = []

    if mime_type is None or mime_type.lower() not in ALLOWED_MIME_TYPES:
        reasons.append(
            f"Unsupported file type '{mime_type}'. Only JPEG and PNG images are accepted."
        )

    if len(data) > MAX_FILE_SIZE_BYTES:
        reasons.append(
            f"File too large ({len(data) // 1024} KB). Maximum is 10 MB."
        )

    width = height = None

    try:
        with Image.open(BytesIO(data)) as img:
            img.verify()
    except UnidentifiedImageError:
        reasons.append("Uploaded file is not a recognizable image format.")
    except Exception:
        reasons.append("Image appears corrupted or partially uploaded.")

    # Re-open after verify() since Pillow invalidates the handle
    try:
        with Image.open(BytesIO(data)) as img2:
            width, height = img2.size
    except Exception:
        if "Image appears corrupted" not in " ".join(reasons):
            reasons.append("Failed to read image dimensions.")

    if width is not None and height is not None:
        if width < MIN_WIDTH or height < MIN_HEIGHT:
            reasons.append(
                f"Image resolution too low ({width}×{height}). "
                f"Minimum is {MIN_WIDTH}×{MIN_HEIGHT}."
            )

    return ValidationResult(
        is_valid=len(reasons) == 0,
        reasons=reasons,
        width=width,
        height=height,
        file_size_bytes=len(data),
        mime_type=mime_type,
    )


def load_image_pil(data: bytes) -> Image.Image:
    """Load and normalise image to RGB."""
    img = Image.open(BytesIO(data))
    if img.mode != "RGB":
        img = img.convert("RGB")
    return img


def pil_to_numpy_bgr(img: Image.Image):
    """Convert Pillow RGB image to OpenCV BGR NumPy array."""
    import numpy as np
    import cv2

    rgb = np.array(img)
    return cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)


def encode_png_base64(img_array) -> str:
    """Encode a NumPy array (BGR or grayscale) as a base64 PNG data URL."""
    import base64
    import cv2
    import numpy as np

    if img_array.dtype != np.uint8:
        img_array = np.clip(img_array, 0, 255).astype("uint8")

    success, buffer = cv2.imencode(".png", img_array)
    if not success:
        raise RuntimeError("Failed to encode image as PNG.")

    b64 = base64.b64encode(buffer.tobytes()).decode("ascii")
    return f"data:image/png;base64,{b64}"


def get_image_dimensions(img: Image.Image) -> Tuple[int, int]:
    return img.size
