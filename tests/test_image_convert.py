"""image_convert 単体テスト."""

from __future__ import annotations

import io

import pytest
from PIL import Image

from src.config import CANVAS_L, MAX_FILE_BYTES
from src.image_convert import (
    clamp_max_side,
    convert_image,
    encode_under_limit,
    fit_to_canvas,
)


def test_fit_to_canvas_landscape_size(rgb_png_bytes: bytes) -> None:
    img = Image.open(io.BytesIO(rgb_png_bytes))
    out = fit_to_canvas(img, CANVAS_L, mode="fit")
    assert out.size == (CANVAS_L[1], CANVAS_L[0])  # 1500 x 1051
    assert out.mode == "RGB"


def test_fit_crop_fills_canvas() -> None:
    img = Image.new("RGB", (1000, 500), (0, 0, 0))
    out = fit_to_canvas(img, CANVAS_L, mode="crop")
    assert out.size == (CANVAS_L[1], CANVAS_L[0])


def test_rgba_composited_to_jpeg(rgba_png_bytes: bytes) -> None:
    result = convert_image(
        rgba_png_bytes, "alpha.png", canvas=CANVAS_L, mode="fit", bg=(255, 255, 255)
    )
    assert result.format == "JPEG"
    assert len(result.data) <= MAX_FILE_BYTES
    assert result.data[:2] == b"\xff\xd8"
    assert result.data[:2] == b"\xff\xd8"


def test_webp_convert(webp_bytes: bytes) -> None:
    result = convert_image(webp_bytes, "a.webp", canvas=CANVAS_L, mode="fit")
    assert result.width == CANVAS_L[1]
    assert result.height == CANVAS_L[0]


def test_clamp_max_side_preserves_ratio() -> None:
    img = Image.new("RGB", (8000, 4000), (1, 2, 3))
    out = clamp_max_side(img, max_side=6144)
    assert max(out.size) == 6144
    assert out.size[0] / out.size[1] == pytest.approx(2.0, rel=1e-3)


def test_encode_under_limit_downscales(noisy_jpeg_bytes: bytes) -> None:
    img = Image.open(io.BytesIO(noisy_jpeg_bytes)).convert("RGB")
    data, quality, warnings, _final = encode_under_limit(img, max_bytes=150_000)
    assert len(data) <= 150_000
    assert quality is not None
    assert warnings
    assert b"\xff\xc0" in data  # baseline SOF0


def test_convert_image_respects_max_bytes(noisy_jpeg_bytes: bytes) -> None:
    result = convert_image(
        noisy_jpeg_bytes,
        "noisy.jpg",
        canvas=CANVAS_L,
        mode="fit",
        max_bytes=200_000,
    )
    assert len(result.data) <= 200_000


def test_cmyk_conversion_warns() -> None:
    img = Image.new("CMYK", (200, 150), (0, 50, 50, 0))
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=90)
    result = convert_image(buf.getvalue(), "cmyk.jpg", canvas=CANVAS_L, mode="fit")
    assert any("CMYK" in w for w in result.warnings)
    assert result.format == "JPEG"
    assert result.data[:2] == b"\xff\xd8"
