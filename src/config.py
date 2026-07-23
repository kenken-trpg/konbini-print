"""プリセットと印刷制限値（domain.json からロード）."""

from __future__ import annotations

from .domain import (
    ContentKind,
    FitMode,
    OutputKind,
    PipelineKind,
    Preset,
    PresetVariant,
    ServiceKind,
    get_preset,
    load_domain,
)

_domain = load_domain()
_pl = _domain.print_limits
_seven = _pl["seven_photo"]
_nw = _pl["network"]

MAX_FILE_BYTES = int(_pl["max_file_bytes"])
MIN_JPEG_QUALITY = int(_pl["min_jpeg_quality"])
DEFAULT_JPEG_QUALITY = int(_pl["default_jpeg_quality"])
DEFAULT_BG = tuple(_pl["default_bg"])  # type: ignore[assignment]

SEVEN_PHOTO_RATIO_MIN = float(_seven["ratio_min"])
SEVEN_PHOTO_RATIO_MAX = float(_seven["ratio_max"])
SEVEN_PHOTO_MIN_PX = tuple(_seven["min_px"])  # type: ignore[assignment]
SEVEN_PHOTO_MAX_SIDE = int(_seven["max_side"])
SEVEN_MAX_PAGES = int(_seven["max_pages"])

NW_MIN_LONG_PX = int(_nw["min_long_px"])
NW_MIN_SHORT_PX = int(_nw["min_short_px"])
NW_MAX_PAGES_A4 = int(_nw["max_pages_a4"])
NW_MAX_PAGES_A3 = int(_nw["max_pages_a3"])

CANVAS_L = _domain.canvases["L"]
CANVAS_2L = _domain.canvases["2L"]
CANVAS_A4 = _domain.canvases["A4"]
CANVAS_SQUARE = _domain.canvases["SQUARE"]
CANVAS_HAGAKI = _domain.canvases["HAGAKI"]

PDF_SPLIT_PAGE_CHOICES = _domain.pdf_split_page_choices

PRESETS = _domain.presets
PRESET_ORDER = _domain.preset_order
SERVICE_LABELS = _domain.service_labels
DOMAIN_VERIFIED_AS_OF = _domain.verified_as_of

IMAGE_EXTENSIONS = _domain.image_extensions
PDF_EXTENSIONS = _domain.pdf_extensions
SUPPORTED_EXTENSIONS = IMAGE_EXTENSIONS | PDF_EXTENSIONS

__all__ = [
    "CANVAS_2L",
    "CANVAS_A4",
    "CANVAS_HAGAKI",
    "CANVAS_L",
    "CANVAS_SQUARE",
    "ContentKind",
    "DEFAULT_BG",
    "DEFAULT_JPEG_QUALITY",
    "DOMAIN_VERIFIED_AS_OF",
    "FitMode",
    "IMAGE_EXTENSIONS",
    "MAX_FILE_BYTES",
    "MIN_JPEG_QUALITY",
    "NW_MAX_PAGES_A3",
    "NW_MAX_PAGES_A4",
    "NW_MIN_LONG_PX",
    "NW_MIN_SHORT_PX",
    "OutputKind",
    "PDF_EXTENSIONS",
    "PDF_SPLIT_PAGE_CHOICES",
    "PRESETS",
    "PRESET_ORDER",
    "PipelineKind",
    "Preset",
    "PresetVariant",
    "SERVICE_LABELS",
    "SEVEN_MAX_PAGES",
    "SEVEN_PHOTO_MAX_SIDE",
    "SEVEN_PHOTO_MIN_PX",
    "SEVEN_PHOTO_RATIO_MAX",
    "SEVEN_PHOTO_RATIO_MIN",
    "SUPPORTED_EXTENSIONS",
    "ServiceKind",
    "get_preset",
]
