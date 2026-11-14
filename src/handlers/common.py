"""pipeline handler 共通ユーティリティ."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from ..config import IMAGE_EXTENSIONS, PDF_EXTENSIONS, Preset
from ..dto import BatchResult, OutputArtifact
from ..filenames import build_filename, sanitize_filename, sanitize_stem
from ..options import ProcessOptions
from ..pdf_convert import (
    PdfConvertResult,
    convert_pdf_compat,
    convert_pdf_rasterize,
    split_pdf_by_pages,
)
from ..validate import validate_image_result, validate_pdf_result

FailFn = Callable[[str, Exception], None]


def ext(name: str) -> str:
    return Path(name).suffix.lower()


def is_image(name: str) -> bool:
    return ext(name) in IMAGE_EXTENSIONS


def is_pdf(name: str) -> bool:
    return ext(name) in PDF_EXTENSIONS


def friendly_error(exc: Exception) -> str:
    msg = str(exc)
    if "cannot identify image file" in msg:
        return "画像として認識できません（壊れているか未対応形式の可能性）。"
    return msg


def image_artifact(
    *,
    name: str,
    data: bytes,
    mime: str,
    width: int,
    height: int,
    fmt: str,
    preset: Preset,
    warnings: list[str],
    targets: list[str],
    source_name: str,
    meta_prefix: str | None = None,
    check_profile: str | None = None,
) -> OutputArtifact:
    meta = meta_prefix or f"{width}×{height} / {fmt}"
    return OutputArtifact(
        name=name,
        data=data,
        mime=mime,
        meta=meta,
        checks=validate_image_result(
            width,
            height,
            len(data),
            preset,
            check_profile=check_profile,
        ),
        warnings=list(warnings),
        targets=list(targets),
        source_name=source_name,
        width=width,
        height=height,
    )


def pdf_artifact(
    *,
    name: str,
    data: bytes,
    page_count: int,
    warnings: list[str],
    targets: list[str],
    source_name: str,
    meta_extra: str = "",
) -> OutputArtifact:
    meta = f"{page_count} ページ"
    if meta_extra:
        meta = f"{meta} / {meta_extra}"
    return OutputArtifact(
        name=name,
        data=data,
        mime="application/pdf",
        meta=meta,
        checks=validate_pdf_result(len(data), page_count),
        warnings=list(warnings),
        targets=list(targets),
        source_name=source_name,
        page_count=page_count,
    )


def convert_pdf_bytes(data: bytes, options: ProcessOptions) -> PdfConvertResult:
    if options.rasterize_pdf:
        return convert_pdf_rasterize(data)
    return convert_pdf_compat(data)


def emit_pdf_parts(
    batch: BatchResult,
    *,
    src_name: str,
    pdf: PdfConvertResult,
    options: ProcessOptions,
    targets: list[str],
    index: int,
    name_stem: str | None = None,
) -> None:
    """1つの PDF 結果を、必要ならページ分割して batch に追加する."""
    stem = name_stem or src_name
    if options.split_pdf:
        parts = split_pdf_by_pages(
            pdf.data, options.pages_per_file, base_warnings=pdf.warnings
        )
    else:
        parts = [pdf]

    multi = len(parts) > 1
    for part_i, part in enumerate(parts, start=1):
        if multi:
            out_name = build_filename(
                sanitize_stem(stem), f"_{index:03d}_p{part_i:02d}", ".pdf"
            )
        else:
            out_name = sanitize_filename(stem, ".pdf", index=index)
        batch.outputs.append(
            pdf_artifact(
                name=out_name,
                data=part.data,
                page_count=part.page_count,
                warnings=part.warnings,
                targets=targets,
                source_name=src_name,
            )
        )
