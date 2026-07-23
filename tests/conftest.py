"""テスト用ヘルパー."""

from __future__ import annotations

import io

import pytest
from PIL import Image, ImageDraw


@pytest.fixture
def rgb_png_bytes() -> bytes:
    img = Image.new("RGB", (800, 600), (30, 144, 255))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


@pytest.fixture
def rgba_png_bytes() -> bytes:
    img = Image.new("RGBA", (400, 300), (255, 0, 0, 128))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


@pytest.fixture
def webp_bytes() -> bytes:
    img = Image.new("RGB", (640, 480), (200, 80, 40))
    buf = io.BytesIO()
    img.save(buf, format="WEBP")
    return buf.getvalue()


@pytest.fixture
def noisy_jpeg_bytes() -> bytes:
    """圧縮しにくい大きめ JPEG（容量制限テスト用）."""
    w, h = 2400, 1800
    img = Image.new("RGB", (w, h))
    draw = ImageDraw.Draw(img)
    for i in range(0, w, 11):
        draw.line([(i, 0), (i, h - 1)], fill=(i % 255, (i * 3) % 255, (i * 7) % 255))
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=95)
    return buf.getvalue()


@pytest.fixture
def simple_pdf_bytes() -> bytes:
    import fitz

    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), "konbini-print test")
    data = doc.tobytes()
    doc.close()
    return data
