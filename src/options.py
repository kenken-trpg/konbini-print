"""処理オプション（UI 非依存）."""

from __future__ import annotations

from dataclasses import dataclass

from .config import DEFAULT_BG, FitMode, NW_MAX_PAGES_A4


@dataclass(frozen=True)
class ProcessOptions:
    fit_mode: FitMode = "fit"
    bg: tuple[int, int, int] = DEFAULT_BG
    rasterize_pdf: bool = False
    # ユーザー選択による PDF ページ分割
    split_pdf: bool = False
    pages_per_file: int = NW_MAX_PAGES_A4
    # pack パイプライン: 出力する variant.suffix の部分集合（None = すべて）
    pack_variant_suffixes: tuple[str, ...] | None = None
    # セブン端カット対策: 内容を内側に寄せて余白を確保
    safe_inset: bool = False

    def __post_init__(self) -> None:
        if self.pages_per_file < 1:
            object.__setattr__(self, "pages_per_file", 1)
