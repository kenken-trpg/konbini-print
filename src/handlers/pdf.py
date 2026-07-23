"""pdf パイプライン（PDF 再保存 / 画像→PDF）."""

from __future__ import annotations

from collections.abc import Sequence

from ..config import Preset
from ..dto import BatchResult, InputFile
from ..image_convert import convert_image
from ..options import ProcessOptions
from ..pdf_convert import jpeg_pages_to_pdf
from .common import FailFn, convert_pdf_bytes, emit_pdf_parts, is_image, is_pdf


def process_pdf(
    inputs: Sequence[InputFile],
    preset: Preset,
    options: ProcessOptions,
    batch: BatchResult,
    fail: FailFn,
    preset_targets: list[str],
) -> BatchResult:
    for idx, src in enumerate(inputs, start=1):
        if is_pdf(src.name):
            try:
                pdf_r = convert_pdf_bytes(src.data, options)
                emit_pdf_parts(
                    batch,
                    src_name=src.name,
                    pdf=pdf_r,
                    options=options,
                    targets=preset_targets,
                    index=idx,
                )
            except Exception as exc:  # noqa: BLE001
                fail(src.name, exc)
        elif is_image(src.name):
            try:
                canvas = preset.canvas or (1654, 2339)
                img_r = convert_image(
                    src.data,
                    src.name,
                    canvas=canvas,
                    mode=options.fit_mode,
                    bg=options.bg,
                    output_format="JPEG",
                    safe_inset=options.safe_inset,
                )
                pdf = jpeg_pages_to_pdf([(img_r.data, img_r.width, img_r.height)])
                pdf.warnings = img_r.warnings + pdf.warnings
                emit_pdf_parts(
                    batch,
                    src_name=src.name,
                    pdf=pdf,
                    options=options,
                    targets=preset_targets,
                    index=idx,
                )
            except Exception as exc:  # noqa: BLE001
                fail(src.name, exc)
        else:
            batch.skipped.append(src.name)
    return batch
