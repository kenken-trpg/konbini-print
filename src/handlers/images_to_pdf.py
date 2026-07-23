"""images_to_pdf パイプライン（複数画像まとめ PDF）."""

from __future__ import annotations

from collections.abc import Sequence

from ..config import Preset, get_preset
from ..dto import BatchResult, InputFile
from ..options import ProcessOptions
from ..pdf_convert import images_to_pdf
from .common import FailFn, convert_pdf_bytes, emit_pdf_parts, is_image, is_pdf


def process_images_to_pdf(
    inputs: Sequence[InputFile],
    preset: Preset,
    options: ProcessOptions,
    batch: BatchResult,
    fail: FailFn,
    preset_targets: list[str],
) -> BatchResult:
    image_items = [(f.data, f.name) for f in inputs if is_image(f.name)]
    pdf_inputs = [f for f in inputs if is_pdf(f.name)]
    for f in inputs:
        if not is_image(f.name) and not is_pdf(f.name):
            batch.skipped.append(f.name)

    if image_items:
        try:
            if preset.canvas is None:
                raise RuntimeError("キャンバス未設定のプリセットです。")
            pdf = images_to_pdf(
                image_items,
                canvas=preset.canvas,
                mode=options.fit_mode,
                bg=options.bg,
                safe_inset=options.safe_inset,
            )
            emit_pdf_parts(
                batch,
                src_name="(複数画像)",
                pdf=pdf,
                options=options,
                targets=preset_targets,
                index=1,
                name_stem="images",
            )
        except Exception as exc:  # noqa: BLE001
            fail("(画像まとめ PDF)", exc)
    elif not pdf_inputs:
        batch.errors.append(("(画像まとめ PDF)", "画像ファイルが必要です。"))

    for idx, src in enumerate(pdf_inputs, start=1):
        try:
            pdf_r = convert_pdf_bytes(src.data, options)
            emit_pdf_parts(
                batch,
                src_name=src.name,
                pdf=pdf_r,
                options=options,
                targets=list(get_preset("pdf_compat").targets),
                index=idx,
            )
        except Exception as exc:  # noqa: BLE001
            fail(src.name, exc)
    return batch
