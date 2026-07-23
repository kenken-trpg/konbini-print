"""pack パイプライン（全用途パック）."""

from __future__ import annotations

from collections.abc import Sequence

from ..config import Preset, get_preset
from ..dto import BatchResult, InputFile
from ..filenames import sanitize_stem
from ..image_convert import convert_image
from ..options import ProcessOptions
from ..pdf_convert import PdfConvertResult
from .common import (
    FailFn,
    convert_pdf_bytes,
    emit_pdf_parts,
    image_artifact,
    is_image,
    is_pdf,
)


def process_pack(
    inputs: Sequence[InputFile],
    preset: Preset,
    options: ProcessOptions,
    batch: BatchResult,
    fail: FailFn,
    _preset_targets: list[str],
) -> BatchResult:
    if not preset.variants:
        batch.errors.append((preset.id, "pack プリセットに variants がありません。"))
        return batch

    variants = preset.variants
    if options.pack_variant_suffixes is not None:
        selected = set(options.pack_variant_suffixes)
        variants = tuple(v for v in variants if v.suffix in selected)
        if not variants:
            batch.errors.append(
                (preset.id, "出力バリアントが選択されていません。")
            )
            return batch

    for idx, src in enumerate(inputs, start=1):
        if is_image(src.name):
            try:
                for variant in variants:
                    result = convert_image(
                        src.data,
                        src.name,
                        canvas=variant.canvas,
                        mode=options.fit_mode,
                        bg=options.bg,
                        output_format="JPEG",
                        safe_inset=options.safe_inset,
                    )
                    out_name = (
                        f"{sanitize_stem(src.name)}_{idx:03d}_{variant.suffix}.jpg"
                    )
                    batch.outputs.append(
                        image_artifact(
                            name=out_name,
                            data=result.data,
                            mime="image/jpeg",
                            width=result.width,
                            height=result.height,
                            fmt=result.format,
                            preset=preset,
                            warnings=result.warnings,
                            targets=list(variant.targets),
                            source_name=src.name,
                            meta_prefix=(
                                f"{variant.suffix} / {result.width}×{result.height}"
                            ),
                            check_profile=variant.check_profile,
                        )
                    )
            except Exception as exc:  # noqa: BLE001
                fail(src.name, exc)
        elif is_pdf(src.name):
            try:
                pdf_r = convert_pdf_bytes(src.data, options)
                emit_pdf_parts(
                    batch,
                    src_name=src.name,
                    pdf=PdfConvertResult(
                        data=pdf_r.data,
                        page_count=pdf_r.page_count,
                        warnings=pdf_r.warnings
                        + ["PDF は文書向け（フォト用紙には画像をアップロード）"],
                    ),
                    options=options,
                    targets=list(get_preset("pdf_compat").targets),
                    index=idx,
                )
            except Exception as exc:  # noqa: BLE001
                fail(src.name, exc)
        else:
            batch.skipped.append(src.name)
    return batch
