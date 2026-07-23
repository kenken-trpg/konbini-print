"""変換オーケストレータ（Streamlit 非依存・テーブル駆動）."""

from __future__ import annotations

from collections.abc import Sequence

from .config import Preset
from .dto import BatchResult, InputFile
from .handlers import HANDLERS
from .handlers.common import friendly_error
from .limits import normalize_input_files, validate_input_batch
from .logging_config import log_exception
from .options import ProcessOptions


def process_files(
    inputs: Sequence[InputFile],
    preset: Preset,
    options: ProcessOptions | None = None,
) -> BatchResult:
    """入力ファイル群をプリセットの pipeline 種別に従って変換する."""
    if options is None:
        options = ProcessOptions()

    validate_input_batch(inputs)
    inputs, content_errors = normalize_input_files(inputs)

    batch = BatchResult()
    if content_errors:
        batch.extend_errors(content_errors)
    if not inputs:
        return batch
    preset_targets = list(preset.targets)

    def fail(source: str, exc: Exception) -> None:
        log_exception("変換失敗", exc, source=source, extra={"preset": preset.id})
        batch.errors.append((source, friendly_error(exc)))

    handler = HANDLERS.get(preset.pipeline)
    if handler is None:
        batch.errors.append(
            (preset.id, f"未対応の pipeline 種別です: {preset.pipeline}")
        )
        return batch
    return handler(inputs, preset, options, batch, fail, preset_targets)
