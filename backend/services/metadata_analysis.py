from dataclasses import dataclass
from typing import Dict, List

from PIL import ExifTags, Image


@dataclass
class MetadataResult:
    has_flag: bool
    flags: List[str]
    raw_exif: Dict[str, str]


EDITING_SOFTWARE_KEYWORDS = [
    "photoshop", "gimp", "pixlr", "lightroom",
    "snapseed", "canva", "paint.net", "affinity",
]


def _extract_exif_dict(img: Image.Image) -> dict:
    exif: Dict[str, str] = {}
    try:
        raw_exif = img.getexif()
        if not raw_exif:
            return exif
        for key, value in raw_exif.items():
            tag = ExifTags.TAGS.get(key, str(key))
            try:
                exif[str(tag)] = str(value)
            except Exception:
                exif[str(tag)] = repr(value)
    except Exception:
        pass
    return exif


def run_metadata_analysis(img: Image.Image) -> MetadataResult:
    """
    Inspect EXIF metadata for editing tool fingerprints and missing fields.
    """
    exif = _extract_exif_dict(img)
    flags: List[str] = []

    if not exif:
        flags.append("No EXIF metadata found; capture device cannot be verified.")

    software_fields = []
    for key in ("Software", "ProcessingSoftware", "ImageDescription"):
        if key in exif:
            software_fields.append(exif[key].lower())

    software_str = " ".join(software_fields)
    for keyword in EDITING_SOFTWARE_KEYWORDS:
        if keyword in software_str:
            flags.append(
                f"Editing software detected in EXIF: '{keyword}'."
            )
            break

    return MetadataResult(
        has_flag=len(flags) > 0,
        flags=flags,
        raw_exif=exif,
    )
