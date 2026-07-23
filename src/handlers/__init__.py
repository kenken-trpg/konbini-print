"""pipeline 種別ごとのハンドラ登録."""

from __future__ import annotations

from .image import process_image
from .images_to_pdf import process_images_to_pdf
from .pack import process_pack
from .pdf import process_pdf

HANDLERS = {
    "pack": process_pack,
    "images_to_pdf": process_images_to_pdf,
    "pdf": process_pdf,
    "image": process_image,
}

__all__ = ["HANDLERS"]
