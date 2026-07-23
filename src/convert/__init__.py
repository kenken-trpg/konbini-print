"""変換層: 画像・PDF・オーケストレーション.

ドメイン数値・プリセットは ``src.domain`` / ``domain.json`` を参照する。
"""

from ..handlers import HANDLERS
from ..image_convert import HEIC_AVAILABLE, convert_image, fit_to_canvas, load_image
from ..matrix import compatibility_matrix, matrix_as_table_rows
from ..options import ProcessOptions
from ..pdf_convert import (
    convert_pdf_compat,
    convert_pdf_rasterize,
    images_to_pdf,
    jpeg_pages_to_pdf,
    split_pdf_by_pages,
)
from ..pipeline import process_files
from ..precheck import InputProbe, probe_input, probe_inputs
from ..preview import (
    add_safe_area_guide,
    make_image_thumbnail,
    preview_bytes_for_artifact,
)

__all__ = [
    "HANDLERS",
    "HEIC_AVAILABLE",
    "InputProbe",
    "ProcessOptions",
    "add_safe_area_guide",
    "compatibility_matrix",
    "convert_image",
    "convert_pdf_compat",
    "convert_pdf_rasterize",
    "fit_to_canvas",
    "images_to_pdf",
    "jpeg_pages_to_pdf",
    "load_image",
    "make_image_thumbnail",
    "matrix_as_table_rows",
    "preview_bytes_for_artifact",
    "probe_input",
    "probe_inputs",
    "process_files",
    "split_pdf_by_pages",
]
