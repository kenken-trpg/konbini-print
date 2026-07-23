"""Streamlit / UI 非依存の入出力 DTO."""

from __future__ import annotations

from dataclasses import dataclass, field

from .validate import CheckItem


@dataclass(frozen=True)
class InputFile:
    """変換パイプラインへの入力（bytes 中心）."""

    name: str
    data: bytes


@dataclass
class OutputArtifact:
    """変換結果アーティファクト（bytes 中心・プレビューは含めない）."""

    name: str
    data: bytes
    mime: str
    meta: str
    checks: list[CheckItem] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    targets: list[str] = field(default_factory=list)
    source_name: str = ""
    width: int | None = None
    height: int | None = None
    page_count: int | None = None
    # セッション軽量化で data を空にした場合の実サイズ
    content_bytes: int | None = None

    @property
    def is_image(self) -> bool:
        return self.mime.startswith("image/")

    @property
    def is_pdf(self) -> bool:
        return self.mime == "application/pdf"

    @property
    def size_bytes(self) -> int:
        return self.content_bytes if self.content_bytes is not None else len(self.data)


@dataclass
class BatchResult:
    outputs: list[OutputArtifact] = field(default_factory=list)
    errors: list[tuple[str, str]] = field(default_factory=list)  # (source, message)
    skipped: list[str] = field(default_factory=list)

    def extend_errors(self, extra: list[tuple[str, str]]) -> None:
        self.errors = list(extra) + self.errors
