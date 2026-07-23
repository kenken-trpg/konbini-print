"""プレビュー用サムネイルの単体テスト."""

from __future__ import annotations

import io

from PIL import Image

from src.preview import THUMB_MAX_SIDE, make_image_thumbnail, preview_bytes_for_artifact


def test_make_image_thumbnail_shrinks(rgb_png_bytes: bytes) -> None:
    thumb = make_image_thumbnail(rgb_png_bytes, max_side=64)
    img = Image.open(io.BytesIO(thumb))
    assert img.format == "JPEG"
    assert max(img.size) <= 64
    assert len(thumb) < len(rgb_png_bytes) or max(img.size) <= 64


def test_make_image_thumbnail_respects_max_side() -> None:
    big = Image.new("RGB", (2000, 1000), (10, 20, 30))
    buf = io.BytesIO()
    big.save(buf, format="PNG")
    thumb = make_image_thumbnail(buf.getvalue(), max_side=THUMB_MAX_SIDE)
    out = Image.open(io.BytesIO(thumb))
    assert max(out.size) <= THUMB_MAX_SIDE


def test_preview_bytes_for_pdf_is_none() -> None:
    assert preview_bytes_for_artifact(b"%PDF-1.4", "application/pdf") is None


def test_preview_bytes_for_image(rgb_png_bytes: bytes) -> None:
    thumb = preview_bytes_for_artifact(rgb_png_bytes, "image/png")
    assert thumb is not None
    assert thumb[:2] == b"\xff\xd8"  # JPEG SOI
