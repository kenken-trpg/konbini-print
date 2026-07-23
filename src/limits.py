"""リソース上限（DoS / OOM 対策）.

既定値は domain.json の resource_limits。環境変数で上書き可能:
- KONBINI_MAX_INPUT_FILES
- KONBINI_MAX_INPUT_TOTAL_BYTES
- KONBINI_MAX_URLS_PER_REQUEST
- KONBINI_MAX_DOWNLOAD_BYTES
- KONBINI_MAX_IMAGE_PIXELS
- KONBINI_MAX_PDF_PAGES
- KONBINI_MAX_RASTERIZE_DPI
- KONBINI_MAX_RASTERIZE_PAGE_DPI_PRODUCT
- KONBINI_ALLOW_URL_FETCH (=0/false/off で URL 取得無効)
- KONBINI_MAX_SESSION_RESULT_BYTES
- KONBINI_MAX_SESSION_OUTPUTS
"""

from __future__ import annotations

import os
from collections.abc import Sequence

from .content_sniff import ContentTypeError, validate_and_normalize_name
from .domain import load_domain
from .dto import InputFile

_defaults = load_domain().resource_limits


def _env_int(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        value = int(raw)
        return value if value > 0 else default
    except ValueError:
        return default


def _env_bool(name: str, default: bool) -> bool:
    raw = os.environ.get(name)
    if raw is None or raw.strip() == "":
        return default
    return raw.strip().lower() not in {"0", "false", "off", "no"}


MAX_INPUT_FILES = _env_int("KONBINI_MAX_INPUT_FILES", int(_defaults["max_input_files"]))
MAX_INPUT_TOTAL_BYTES = _env_int(
    "KONBINI_MAX_INPUT_TOTAL_BYTES", int(_defaults["max_input_total_bytes"])
)
MAX_URLS_PER_REQUEST = _env_int(
    "KONBINI_MAX_URLS_PER_REQUEST", int(_defaults["max_urls_per_request"])
)
MAX_DOWNLOAD_BYTES = _env_int(
    "KONBINI_MAX_DOWNLOAD_BYTES", int(_defaults["max_download_bytes"])
)
MAX_IMAGE_PIXELS = _env_int(
    "KONBINI_MAX_IMAGE_PIXELS", int(_defaults["max_image_pixels"])
)
MAX_PDF_PAGES = _env_int("KONBINI_MAX_PDF_PAGES", int(_defaults["max_pdf_pages"]))
MAX_RASTERIZE_DPI = _env_int(
    "KONBINI_MAX_RASTERIZE_DPI", int(_defaults["max_rasterize_dpi"])
)
MAX_RASTERIZE_PAGE_DPI_PRODUCT = _env_int(
    "KONBINI_MAX_RASTERIZE_PAGE_DPI_PRODUCT",
    int(_defaults.get("max_rasterize_page_dpi_product", 8000)),
)
ALLOW_URL_FETCH = _env_bool(
    "KONBINI_ALLOW_URL_FETCH", bool(_defaults.get("allow_url_fetch", True))
)
MAX_SESSION_RESULT_BYTES = _env_int(
    "KONBINI_MAX_SESSION_RESULT_BYTES",
    int(_defaults.get("max_session_result_bytes", 50 * 1024 * 1024)),
)
MAX_SESSION_OUTPUTS = _env_int(
    "KONBINI_MAX_SESSION_OUTPUTS",
    int(_defaults.get("max_session_outputs", 30)),
)


class ResourceLimitError(ValueError):
    """入力リソース上限超過."""


def validate_input_batch(inputs: Sequence[InputFile]) -> None:
    """変換前の入力バッチ上限を検証する."""
    if len(inputs) > MAX_INPUT_FILES:
        raise ResourceLimitError(
            f"ファイル数が上限を超えています（最大 {MAX_INPUT_FILES} 件、現在 {len(inputs)} 件）。"
        )
    total = sum(len(f.data) for f in inputs)
    if total > MAX_INPUT_TOTAL_BYTES:
        raise ResourceLimitError(
            f"入力合計サイズが上限を超えています"
            f"（最大 {MAX_INPUT_TOTAL_BYTES // 1024 // 1024}MB、"
            f"現在 {total / 1024 / 1024:.1f}MB）。"
        )


def normalize_input_files(
    inputs: Sequence[InputFile],
) -> tuple[list[InputFile], list[tuple[str, str]]]:
    """マジックバイトで実体検証し、必要なら拡張子を補正する.

    不正なファイルはエラー一覧へ回し、バッチ全体は止めない。
    """
    out: list[InputFile] = []
    errors: list[tuple[str, str]] = []
    for f in inputs:
        try:
            new_name, _kind = validate_and_normalize_name(f.name, f.data)
        except ContentTypeError as exc:
            errors.append((f.name, str(exc)))
            continue
        out.append(InputFile(name=new_name, data=f.data) if new_name != f.name else f)
    return out, errors


def clamp_rasterize_dpi(dpi: int) -> int:
    return max(36, min(int(dpi), MAX_RASTERIZE_DPI))


def ensure_pdf_page_limit(page_count: int) -> None:
    if page_count > MAX_PDF_PAGES:
        raise ResourceLimitError(
            f"PDF ページ数が上限を超えています（最大 {MAX_PDF_PAGES}、現在 {page_count}）。"
        )


def session_result_within_limits(output_count: int, total_bytes: int) -> bool:
    return (
        output_count <= MAX_SESSION_OUTPUTS
        and total_bytes <= MAX_SESSION_RESULT_BYTES
    )


def would_exceed_input_total(current_bytes: int, adding: int) -> bool:
    """入力合計上限を超えるか（追加前の判定用）."""
    return current_bytes + max(0, adding) > MAX_INPUT_TOTAL_BYTES

