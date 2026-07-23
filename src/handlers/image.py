"""image パイプライン（単一キャンバス画像変換）."""

from __future__ import annotations

from collections.abc import Sequence

from ..config import Preset
from ..dto import BatchResult, InputFile
from ..filenames import sanitize_filename
from ..image_convert import convert_image
from ..options import ProcessOptions
from .common import FailFn, image_artifact, is_image, is_pdf


def process_image(
    inputs: Sequence[InputFile],
    preset: Preset,
    options: ProcessOptions,
    batch: BatchResult,
    fail: FailFn,
    preset_targets: list[str],
) -> BatchResult:
    for idx, src in enumerate(inputs, start=1):
        if is_image(src.name):
            try:
                out_fmt = "JPEG" if preset.output == "jpeg" else "PNG"
                result = convert_image(
                    src.data,
                    src.name,
                    canvas=preset.canvas,
                    mode=options.fit_mode,
                    bg=options.bg,
                    output_format=out_fmt,
                    safe_inset=options.safe_inset,
                )
                ext = ".jpg" if result.format == "JPEG" else ".png"
                mime = "image/jpeg" if result.format == "JPEG" else "image/png"
                batch.outputs.append(
                    image_artifact(
                        name=sanitize_filename(src.name, ext, index=idx),
                        data=result.data,
                        mime=mime,
                        width=result.width,
                        height=result.height,
                        fmt=result.format,
                        preset=preset,
                        warnings=result.warnings,
                        targets=preset_targets,
                        source_name=src.name,
                    )
                )
            except Exception as exc:  # noqa: BLE001
                fail(src.name, exc)
        elif is_pdf(src.name):
            batch.skipped.append(
                f"{src.name}（画像プリセットのためスキップ。PDF再保存プリセットを利用）"
            )
        else:
            batch.skipped.append(src.name)
    return batch
