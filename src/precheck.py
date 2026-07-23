"""変換前の入力プローブ（形式・容量・寸法・ファイル名）."""

from __future__ import annotations

import io
from dataclasses import dataclass, field
from pathlib import Path

from PIL import ImageOps

from .config import IMAGE_EXTENSIONS, PDF_EXTENSIONS
from .dto import InputFile
from .filenames import filename_changed, sanitize_filename, sanitize_stem
from .validate import aspect_ratio


@dataclass
class InputProbe:
    name: str
    kind: str  # image | pdf | unknown
    size_bytes: int
    width: int | None = None
    height: int | None = None
    ratio: float | None = None
    format_hint: str = ""
    page_count: int | None = None
    sanitized_stem: str = ""
    name_will_change: bool = False
    notes: list[str] = field(default_factory=list)

    @property
    def size_label(self) -> str:
        return f"{self.size_bytes / 1024:.1f} KB"

    @property
    def dim_label(self) -> str:
        if self.width and self.height:
            extra = f" / 比 {self.ratio:.3f}" if self.ratio else ""
            return f"{self.width}×{self.height}{extra}"
        if self.page_count is not None:
            return f"{self.page_count} ページ"
        return "—"


def probe_input(src: InputFile) -> InputProbe:
    """変換せずに入力の概要を取得する."""
    ext = Path(src.name).suffix.lower()
    stem = sanitize_stem(src.name)
    probe = InputProbe(
        name=src.name,
        kind="unknown",
        size_bytes=len(src.data),
        sanitized_stem=stem,
        name_will_change=filename_changed(src.name, stem),
    )

    if ext in IMAGE_EXTENSIONS:
        probe.kind = "image"
        try:
            from .image_convert import load_image

            img = load_image(src.data, src.name)
            img = ImageOps.exif_transpose(img)
            w, h = img.size
            probe.width, probe.height = w, h
            probe.ratio = aspect_ratio(w, h)
            probe.format_hint = (img.format or ext.lstrip(".")).upper()
            if img.mode == "CMYK":
                probe.notes.append("CMYK（変換時に RGB 化）")
            if img.mode in {"RGBA", "LA"} or (
                img.mode == "P" and "transparency" in img.info
            ):
                probe.notes.append("透過あり（不透明化）")
        except Exception as exc:  # noqa: BLE001
            probe.notes.append(f"画像として読めません: {exc}")
    elif ext in PDF_EXTENSIONS:
        probe.kind = "pdf"
        probe.format_hint = "PDF"
        try:
            from pypdf import PdfReader

            reader = PdfReader(io.BytesIO(src.data))
            if reader.is_encrypted:
                probe.notes.append("暗号化 PDF（変換不可）")
            probe.page_count = len(reader.pages)
        except Exception as exc:  # noqa: BLE001
            probe.notes.append(f"PDF として読めません: {exc}")
    else:
        probe.notes.append("未対応の拡張子の可能性")

    if probe.name_will_change:
        example = sanitize_filename(src.name, ext or ".bin")
        probe.notes.append(f"出力ファイル名: {example}")

    return probe


def probe_inputs(files: list[InputFile]) -> list[InputProbe]:
    return [probe_input(f) for f in files]
