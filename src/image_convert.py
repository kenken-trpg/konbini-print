"""画像読み込み・フィット・圧縮."""

from __future__ import annotations

import io
from dataclasses import dataclass

from PIL import Image, ImageOps

from .config import (
    DEFAULT_BG,
    DEFAULT_JPEG_QUALITY,
    MAX_FILE_BYTES,
    MIN_JPEG_QUALITY,
    SEVEN_PHOTO_MAX_SIDE,
    FitMode,
)
from .limits import MAX_IMAGE_PIXELS

# HEIC 登録（利用不可でもアプリは起動できるようにする）
HEIC_AVAILABLE = False
try:
    from pillow_heif import register_heif_opener

    register_heif_opener()
    HEIC_AVAILABLE = True
except Exception:  # noqa: BLE001
    HEIC_AVAILABLE = False

# デコンプレッション爆弾対策
Image.MAX_IMAGE_PIXELS = MAX_IMAGE_PIXELS


@dataclass
class ImageConvertResult:
    data: bytes
    format: str  # JPEG / PNG
    width: int
    height: int
    quality: int | None
    warnings: list[str]


def _to_rgb(img: Image.Image, bg: tuple[int, int, int] = DEFAULT_BG) -> Image.Image:
    img = ImageOps.exif_transpose(img)
    if img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info):
        rgba = img.convert("RGBA")
        background = Image.new("RGBA", rgba.size, (*bg, 255))
        composited = Image.alpha_composite(background, rgba)
        return composited.convert("RGB")
    if img.mode != "RGB":
        return img.convert("RGB")
    return img


def load_image(data: bytes, filename: str = "") -> Image.Image:
    lower = filename.lower()
    if lower.endswith((".heic", ".heif")) and not HEIC_AVAILABLE:
        raise RuntimeError(
            "HEIC を読めません。pillow-heif / libheif が利用可能か確認してください。"
        )
    try:
        img = Image.open(io.BytesIO(data))
        # ヘッダ上のピクセル数を先に拒否（展開前）
        w, h = img.size
        if w * h > MAX_IMAGE_PIXELS:
            raise RuntimeError(
                f"画像ピクセル数が上限を超えています"
                f"（最大 {MAX_IMAGE_PIXELS:,}、現在 {w * h:,}）。"
            )
        img.load()
    except Image.DecompressionBombError as exc:
        raise RuntimeError(
            f"画像が大きすぎます（ピクセル上限 {MAX_IMAGE_PIXELS:,}）。"
        ) from exc
    if getattr(img, "n_frames", 1) > 1:
        img.seek(0)
    return img


def clamp_max_side(img: Image.Image, max_side: int = SEVEN_PHOTO_MAX_SIDE) -> Image.Image:
    """長辺が上限を超える場合のみアスペクト比を保って縮小する."""
    w, h = img.size
    long_side = max(w, h)
    if long_side <= max_side:
        return img
    scale = max_side / long_side
    new_size = (max(1, int(w * scale)), max(1, int(h * scale)))
    return img.resize(new_size, Image.Resampling.LANCZOS)


def fit_to_canvas(
    img: Image.Image,
    canvas: tuple[int, int],
    mode: FitMode = "fit",
    bg: tuple[int, int, int] = DEFAULT_BG,
) -> Image.Image:
    """canvas は (短辺, 長辺) の縦向き基準。入力の向きに合わせて回転する."""
    rgb = _to_rgb(img, bg)
    short, long = canvas
    src_w, src_h = rgb.size
    src_landscape = src_w >= src_h

    if src_landscape:
        target_w, target_h = long, short
    else:
        target_w, target_h = short, long

    if mode == "crop":
        return ImageOps.fit(rgb, (target_w, target_h), method=Image.Resampling.LANCZOS)

    # fit: 全体を収め、余白を埋める
    fitted = ImageOps.contain(rgb, (target_w, target_h), method=Image.Resampling.LANCZOS)
    canvas_img = Image.new("RGB", (target_w, target_h), bg)
    offset = ((target_w - fitted.width) // 2, (target_h - fitted.height) // 2)
    canvas_img.paste(fitted, offset)
    return canvas_img


def _encode_jpeg(img: Image.Image, quality: int) -> bytes:
    buf = io.BytesIO()
    # baseline JPEG（progressive は一部複合機と相性が悪い）
    img.save(buf, format="JPEG", quality=quality, optimize=True, progressive=False)
    return buf.getvalue()


def encode_under_limit(
    img: Image.Image,
    fmt: str = "JPEG",
    max_bytes: int = MAX_FILE_BYTES,
    start_quality: int = DEFAULT_JPEG_QUALITY,
    min_quality: int = MIN_JPEG_QUALITY,
    min_long_side: int = 640,
) -> tuple[bytes, int | None, list[str], Image.Image]:
    """容量制限内に収まるよう品質低下→解像度縮小の順でエンコードする.

    Returns:
        (bytes, jpeg_quality_or_None, warnings, final_image)
    """
    warnings: list[str] = []
    fmt = fmt.upper()
    if fmt == "JPG":
        fmt = "JPEG"

    current = img

    if fmt == "PNG":
        buf = io.BytesIO()
        current.save(buf, format="PNG", optimize=True)
        data = buf.getvalue()
        if len(data) <= max_bytes:
            return data, None, warnings, current
        warnings.append(
            f"PNG が {len(data) / 1024 / 1024:.1f}MB で上限超過のため JPEG に切替えます。"
        )
        fmt = "JPEG"

    scale_round = 0
    data = b""
    quality = start_quality

    while True:
        quality = start_quality
        while quality >= min_quality:
            data = _encode_jpeg(current, quality)
            if len(data) <= max_bytes:
                if quality < start_quality or scale_round > 0:
                    msg_parts = []
                    if quality < start_quality:
                        msg_parts.append(f"JPEG 品質 {quality}")
                    if scale_round > 0:
                        msg_parts.append(
                            f"解像度 {current.width}×{current.height}"
                        )
                    warnings.append(
                        "容量制限のため " + " / ".join(msg_parts) + " に調整しました。"
                    )
                return data, quality, warnings, current
            quality -= 5

        long_side = max(current.size)
        if long_side <= min_long_side:
            warnings.append(
                f"下限品質・最小解像度付近でも {len(data) / 1024 / 1024:.1f}MB です。"
                "ページ分割や別プリセットを検討してください。"
            )
            return data, min_quality, warnings, current

        scale = 0.85
        new_size = (
            max(1, int(current.width * scale)),
            max(1, int(current.height * scale)),
        )
        current = current.resize(new_size, Image.Resampling.LANCZOS)
        scale_round += 1


def apply_safe_inset(
    img: Image.Image,
    *,
    inset_ratio: float = 0.03,
    bg: tuple[int, int, int] = DEFAULT_BG,
) -> Image.Image:
    """端カットを見越し、内容を内側に寄せて余白（塗り足し相当のセーフ領域）を作る."""
    if inset_ratio <= 0:
        return img
    w, h = img.size
    ix = max(1, int(w * inset_ratio))
    iy = max(1, int(h * inset_ratio))
    inner = (max(1, w - 2 * ix), max(1, h - 2 * iy))
    fitted = ImageOps.contain(img, inner, method=Image.Resampling.LANCZOS)
    canvas = Image.new("RGB", (w, h), bg)
    offset = ((w - fitted.width) // 2, (h - fitted.height) // 2)
    canvas.paste(fitted, offset)
    return canvas


def convert_image(
    data: bytes,
    filename: str,
    canvas: tuple[int, int] | None,
    mode: FitMode = "fit",
    bg: tuple[int, int, int] = DEFAULT_BG,
    output_format: str = "JPEG",
    max_bytes: int = MAX_FILE_BYTES,
    *,
    safe_inset: bool = False,
    safe_inset_ratio: float = 0.03,
) -> ImageConvertResult:
    img = load_image(data, filename)
    warnings: list[str] = []
    if img.mode == "CMYK":
        warnings.append(
            "CMYK を RGB に変換しました（色が変わることがあります）。"
        )

    if canvas is None:
        rgb = _to_rgb(img, bg)
        out = clamp_max_side(rgb)
        if out.size != rgb.size:
            warnings.append(
                f"長辺が {SEVEN_PHOTO_MAX_SIDE}px を超えていたため縮小しました。"
            )
    else:
        out = fit_to_canvas(img, canvas, mode=mode, bg=bg)

    if safe_inset:
        out = apply_safe_inset(out, inset_ratio=safe_inset_ratio, bg=bg)
        warnings.append(
            f"セーフエリア（内側約 {safe_inset_ratio * 100:.0f}%）を確保しました。"
            "セブンの端カット対策です。"
        )

    encoded, quality, enc_warns, final_img = encode_under_limit(
        out, fmt=output_format, max_bytes=max_bytes
    )
    warnings.extend(enc_warns)
    if encoded[:2] == b"\xff\xd8":
        fmt = "JPEG"
    elif encoded[:8] == b"\x89PNG\r\n\x1a\n":
        fmt = "PNG"
    else:
        fmt = "JPEG" if output_format.upper() in {"JPEG", "JPG"} else "PNG"

    return ImageConvertResult(
        data=encoded,
        format=fmt,
        width=final_img.width,
        height=final_img.height,
        quality=quality,
        warnings=warnings,
    )
