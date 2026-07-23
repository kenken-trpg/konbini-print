"""PDF 互換化・画像からの PDF 生成."""

from __future__ import annotations

import io
from dataclasses import dataclass, field

from pypdf import PdfReader, PdfWriter
from pypdf.errors import PdfReadError

from .config import MAX_FILE_BYTES, NW_MAX_PAGES_A4, SEVEN_MAX_PAGES
from .image_convert import convert_image, FitMode
from .limits import (
    MAX_PDF_PAGES,
    MAX_RASTERIZE_PAGE_DPI_PRODUCT,
    clamp_rasterize_dpi,
    ensure_pdf_page_limit,
)
from .targets import PDF_COMPAT_HONEST


@dataclass
class PdfConvertResult:
    data: bytes
    page_count: int
    warnings: list[str] = field(default_factory=list)
    source_was_encrypted: bool = False


def _page_warnings(page_count: int) -> list[str]:
    warns: list[str] = []
    if page_count > NW_MAX_PAGES_A4:
        warns.append(
            f"ネットワークプリント（A4系）は目安 {NW_MAX_PAGES_A4} ページまでです（現在 {page_count}）。"
        )
    if page_count > SEVEN_MAX_PAGES:
        warns.append(f"セブンネットプリントは {SEVEN_MAX_PAGES} ページ超を登録できません（現在 {page_count}）。")
    return warns


def convert_pdf_compat(data: bytes, max_bytes: int = MAX_FILE_BYTES) -> PdfConvertResult:
    """暗号化チェック後、ページを書き直して非暗号化 PDF を生成する.

    注: PDF 1.4 強制や注釈・フォント問題の完全解消は行いません。
    """
    warnings: list[str] = [PDF_COMPAT_HONEST]
    try:
        reader = PdfReader(io.BytesIO(data))
    except PdfReadError as exc:
        raise RuntimeError(f"PDF を読めません: {exc}") from exc

    if reader.is_encrypted:
        # 空パスワード試行
        try:
            ok = reader.decrypt("")
        except Exception:  # noqa: BLE001
            ok = 0
        if not ok:
            raise RuntimeError(
                "パスワード付き PDF です。解除してからアップロードしてください。"
            )
        warnings.append("空パスワードで復号しました。出力は非暗号化です。")

    page_count = len(reader.pages)
    ensure_pdf_page_limit(page_count)

    writer = PdfWriter()
    for page in reader.pages:
        writer.add_page(page)

    writer.add_metadata({"/Producer": "konbini-print", "/Creator": "konbini-print"})

    out = io.BytesIO()
    writer.write(out)
    result_data = out.getvalue()
    warnings.extend(_page_warnings(page_count))

    if len(result_data) > max_bytes:
        warnings.append(
            f"PDF が {len(result_data) / 1024 / 1024:.1f}MB で 10MB 超です。"
            "ページ分割か「ラスタライズ互換」を試してください。"
        )

    return PdfConvertResult(data=result_data, page_count=page_count, warnings=warnings)


def convert_pdf_rasterize(
    data: bytes,
    dpi: int = 150,
    max_bytes: int = MAX_FILE_BYTES,
) -> PdfConvertResult:
    """各ページを画像化して再構成（互換性優先・画質トレードオフ）.

    ページ×DPI 積で解像度を抑え、pixmap はページごとに解放する。
    容量超過時は再帰せず DPI を下げて同一ドキュメント上で再試行する。
    """
    import fitz  # PyMuPDF

    dpi = clamp_rasterize_dpi(dpi)
    warnings: list[str] = ["ページを画像化して再構成しました（互換性優先）。"]
    try:
        doc = fitz.open(stream=data, filetype="pdf")
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(f"PDF を開けません: {exc}") from exc

    if doc.is_encrypted:
        try:
            if not doc.authenticate(""):
                raise RuntimeError(
                    "パスワード付き PDF です。解除してからアップロードしてください。"
                )
        except RuntimeError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise RuntimeError(
                "パスワード付き PDF です。解除してからアップロードしてください。"
            ) from exc

    try:
        ensure_pdf_page_limit(doc.page_count)
    except Exception:
        doc.close()
        raise

    page_count = doc.page_count
    # ページ数が多いと pixmap ピークが膨らむため、積上限で DPI を先に下げる
    if page_count * dpi > MAX_RASTERIZE_PAGE_DPI_PRODUCT:
        capped = max(72, MAX_RASTERIZE_PAGE_DPI_PRODUCT // max(1, page_count))
        dpi = clamp_rasterize_dpi(capped)
        warnings.append(
            f"ページ数（{page_count}）が多いため、メモリ対策で {dpi}dpi に下げました。"
        )

    result_data = b""
    try:
        while True:
            out_doc = fitz.open()
            zoom = dpi / 72.0
            matrix = fitz.Matrix(zoom, zoom)
            try:
                for page in doc:
                    pix = page.get_pixmap(matrix=matrix, alpha=False)
                    try:
                        img_bytes = pix.tobytes("jpeg")
                        rect = fitz.Rect(0, 0, pix.width, pix.height)
                        new_page = out_doc.new_page(width=pix.width, height=pix.height)
                        new_page.insert_image(rect, stream=img_bytes)
                    finally:
                        del pix

                result_data = out_doc.tobytes(deflate=True, garbage=3)
            finally:
                out_doc.close()

            if len(result_data) <= max_bytes or dpi <= 100:
                break
            dpi = max(72, dpi - 30)
            warnings.append(f"容量超過のため {dpi}dpi で再ラスタライズします。")
    finally:
        doc.close()

    if len(result_data) > max_bytes:
        warnings.append(
            f"ラスタライズ後も {len(result_data) / 1024 / 1024:.1f}MB です。"
            "ページ分割を検討してください。"
        )

    warnings.extend(_page_warnings(page_count))
    return PdfConvertResult(data=result_data, page_count=page_count, warnings=warnings)


def jpeg_pages_to_pdf(
    pages: list[tuple[bytes, int, int]],
    max_bytes: int = MAX_FILE_BYTES,
) -> PdfConvertResult:
    """既に JPEG 化したページ (bytes, width, height) から PDF を組み立てる."""
    import fitz

    warnings: list[str] = []
    out_doc = fitz.open()
    for jpeg_bytes, width, height in pages:
        rect = fitz.Rect(0, 0, width, height)
        page = out_doc.new_page(width=width, height=height)
        page.insert_image(rect, stream=jpeg_bytes)

    result_data = out_doc.tobytes(deflate=True, garbage=3)
    page_count = out_doc.page_count
    warnings.extend(_page_warnings(page_count))
    if len(result_data) > max_bytes:
        warnings.append(
            f"まとめ PDF が {len(result_data) / 1024 / 1024:.1f}MB で上限超過です。"
        )
    out_doc.close()
    return PdfConvertResult(data=result_data, page_count=page_count, warnings=warnings)


def split_pdf_by_pages(
    data: bytes,
    pages_per_file: int,
    base_warnings: list[str] | None = None,
) -> list[PdfConvertResult]:
    """PDF を指定ページ数ごとに分割する（ユーザー選択用）."""
    if pages_per_file < 1:
        raise ValueError("pages_per_file は 1 以上です。")

    try:
        reader = PdfReader(io.BytesIO(data))
    except PdfReadError as exc:
        raise RuntimeError(f"PDF を読めません: {exc}") from exc

    if reader.is_encrypted:
        try:
            ok = reader.decrypt("")
        except Exception:  # noqa: BLE001
            ok = 0
        if not ok:
            raise RuntimeError(
                "パスワード付き PDF です。解除してからアップロードしてください。"
            )

    total = len(reader.pages)
    if total == 0:
        raise RuntimeError("ページがありません。")
    ensure_pdf_page_limit(total)

    # 分割不要
    if total <= pages_per_file:
        single = PdfConvertResult(
            data=data,
            page_count=total,
            warnings=list(base_warnings or [])
            + [f"分割不要（全 {total} ページ ≤ {pages_per_file}）"],
        )
        return [single]

    parts: list[PdfConvertResult] = []
    part_index = 1
    for start in range(0, total, pages_per_file):
        writer = PdfWriter()
        chunk = reader.pages[start : start + pages_per_file]
        for page in chunk:
            writer.add_page(page)
        writer.add_metadata(
            {"/Producer": "konbini-print", "/Creator": "konbini-print"}
        )
        out = io.BytesIO()
        writer.write(out)
        page_count = len(chunk)
        warns = list(base_warnings or [])
        warns.append(
            f"分割パート {part_index}: ページ {start + 1}–{start + page_count} / 全 {total}"
            f"（{pages_per_file} ページごと）"
        )
        warns.extend(_page_warnings(page_count))
        result_data = out.getvalue()
        if len(result_data) > MAX_FILE_BYTES:
            warns.append(
                f"分割後も {len(result_data) / 1024 / 1024:.1f}MB です。"
                "ページ数をさらに減らしてください。"
            )
        parts.append(
            PdfConvertResult(data=result_data, page_count=page_count, warnings=warns)
        )
        part_index += 1
    return parts


def images_to_pdf(
    items: list[tuple[bytes, str]],
    canvas: tuple[int, int],
    mode: FitMode = "fit",
    bg: tuple[int, int, int] = (255, 255, 255),
    max_bytes: int = MAX_FILE_BYTES,
    *,
    safe_inset: bool = False,
) -> PdfConvertResult:
    """画像群を A4 相当ページの PDF にまとめる."""
    warnings: list[str] = []
    pages: list[tuple[bytes, int, int]] = []

    for data, name in items:
        converted = convert_image(
            data,
            name,
            canvas=canvas,
            mode=mode,
            bg=bg,
            output_format="JPEG",
            max_bytes=max_bytes,
            safe_inset=safe_inset,
        )
        warnings.extend(converted.warnings)
        pages.append((converted.data, converted.width, converted.height))

    result = jpeg_pages_to_pdf(pages, max_bytes=max_bytes)
    result.warnings = warnings + result.warnings
    return result
