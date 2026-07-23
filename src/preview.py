"""UI 向けプレビュー用サムネイル生成（Streamlit 非依存）."""

from __future__ import annotations

import io

from PIL import Image, ImageDraw, ImageOps

# セッション表示用。フル解像度はダウンロード専用に残す。
THUMB_MAX_SIDE = 512
THUMB_JPEG_QUALITY = 72
# セブン端カット目安（用紙端からおおよそ数 mm）
SAFE_AREA_INSET_RATIO = 0.03


def make_image_thumbnail(
    data: bytes,
    *,
    max_side: int = THUMB_MAX_SIDE,
    quality: int = THUMB_JPEG_QUALITY,
) -> bytes:
    """画像 bytes から縮小 JPEG サムネを返す."""
    img = Image.open(io.BytesIO(data))
    img = ImageOps.exif_transpose(img)
    if img.mode not in {"RGB", "L"}:
        img = img.convert("RGB")
    elif img.mode == "L":
        img = img.convert("RGB")
    img.thumbnail((max_side, max_side), Image.Resampling.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=quality, optimize=True)
    return buf.getvalue()


def add_safe_area_guide(
    jpeg_bytes: bytes,
    *,
    inset_ratio: float = SAFE_AREA_INSET_RATIO,
) -> bytes:
    """プレビューにセーフエリア枠を重ねる（端カット目安）."""
    img = Image.open(io.BytesIO(jpeg_bytes)).convert("RGB")
    draw = ImageDraw.Draw(img)
    w, h = img.size
    ix = max(1, int(w * inset_ratio))
    iy = max(1, int(h * inset_ratio))
    box = [ix, iy, w - ix - 1, h - iy - 1]
    # 視認しやすい二重線
    draw.rectangle(box, outline=(255, 64, 64), width=2)
    draw.rectangle(
        [ix + 2, iy + 2, w - ix - 3, h - iy - 3],
        outline=(255, 200, 200),
        width=1,
    )
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=THUMB_JPEG_QUALITY, optimize=True)
    return buf.getvalue()


def preview_bytes_for_artifact(data: bytes, mime: str) -> bytes | None:
    """プレビュー用 bytes。画像のみサムネ、PDF 等は None."""
    if not mime.startswith("image/"):
        return None
    try:
        return make_image_thumbnail(data)
    except Exception:  # noqa: BLE001
        return None
