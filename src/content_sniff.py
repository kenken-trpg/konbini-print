"""コンテンツ種別のマジックバイト検出（拡張子偽装対策）."""

from __future__ import annotations

from pathlib import Path

# 拡張子 → 許容する検出種別
_EXT_TO_KINDS: dict[str, frozenset[str]] = {
    ".jpg": frozenset({"jpeg"}),
    ".jpeg": frozenset({"jpeg"}),
    ".jpe": frozenset({"jpeg"}),
    ".png": frozenset({"png"}),
    ".webp": frozenset({"webp"}),
    ".gif": frozenset({"gif"}),
    ".tif": frozenset({"tiff"}),
    ".tiff": frozenset({"tiff"}),
    ".bmp": frozenset({"bmp"}),
    ".heic": frozenset({"heic"}),
    ".heif": frozenset({"heic"}),
    ".pdf": frozenset({"pdf"}),
}

_KIND_TO_EXT: dict[str, str] = {
    "jpeg": ".jpg",
    "png": ".png",
    "webp": ".webp",
    "gif": ".gif",
    "tiff": ".tiff",
    "bmp": ".bmp",
    "heic": ".heic",
    "pdf": ".pdf",
}


class ContentTypeError(ValueError):
    """拡張子と実体の不一致、または未対応形式."""


def sniff_kind(data: bytes) -> str | None:
    """マジックバイトから種別を返す。不明なら None."""
    if not data or len(data) < 12:
        # 短い PDF ヘッダだけでも判定
        if data.startswith(b"%PDF"):
            return "pdf"
        return None

    if data.startswith(b"%PDF"):
        return "pdf"
    if data.startswith(b"\xff\xd8\xff"):
        return "jpeg"
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png"
    if data.startswith(b"GIF87a") or data.startswith(b"GIF89a"):
        return "gif"
    if data.startswith(b"BM"):
        return "bmp"
    if data.startswith(b"II*\x00") or data.startswith(b"MM\x00*"):
        return "tiff"
    if data.startswith(b"RIFF") and data[8:12] == b"WEBP":
        return "webp"
    # HEIC/HEIF: ....ftyp + brand
    if len(data) >= 12 and data[4:8] == b"ftyp":
        brand = data[8:12]
        if brand in {b"heic", b"heif", b"mif1", b"msf1", b"heim", b"heis"}:
            return "heic"
    return None


def validate_and_normalize_name(name: str, data: bytes) -> tuple[str, str]:
    """実体を検証し、必要なら拡張子を補正したファイル名と種別を返す.

    Raises:
        ContentTypeError: 未対応、または拡張子と実体が矛盾する場合
    """
    kind = sniff_kind(data)
    if kind is None:
        raise ContentTypeError(
            "対応形式として認識できません（JPEG/PNG/WebP/GIF/TIFF/BMP/HEIC/PDF）。"
            "拡張子だけの偽装ファイルの可能性があります。"
        )

    ext = Path(name).suffix.lower()
    stem = Path(name).stem or "file"

    if ext in _EXT_TO_KINDS:
        allowed = _EXT_TO_KINDS[ext]
        if kind not in allowed:
            raise ContentTypeError(
                f"拡張子 {ext} と実体（{kind}）が一致しません。"
                "拡張子偽装の可能性があるため拒否しました。"
            )
        return name, kind

    # 拡張子なし / 未知 → magic に合わせて付与
    new_ext = _KIND_TO_EXT[kind]
    return f"{stem}{new_ext}", kind


def is_supported_payload(data: bytes) -> bool:
    return sniff_kind(data) is not None
