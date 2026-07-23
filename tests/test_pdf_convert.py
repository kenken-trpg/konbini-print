"""pdf_convert 単体テスト."""

import pytest

from src.pdf_convert import convert_pdf_compat, convert_pdf_rasterize, jpeg_pages_to_pdf
from src.targets import PDF_COMPAT_HONEST


def test_convert_pdf_compat_adds_honest_warning(simple_pdf_bytes: bytes) -> None:
    result = convert_pdf_compat(simple_pdf_bytes)
    assert result.page_count == 1
    assert result.data.startswith(b"%PDF")
    assert any(PDF_COMPAT_HONEST[:20] in w or "保証しません" in w for w in result.warnings)


def test_convert_pdf_compat_rejects_encrypted() -> None:
    from pypdf import PdfWriter
    import io

    writer = PdfWriter()
    writer.add_blank_page(width=200, height=200)
    writer.encrypt("secret")
    buf = io.BytesIO()
    writer.write(buf)
    with pytest.raises(RuntimeError, match="パスワード"):
        convert_pdf_compat(buf.getvalue())


def test_jpeg_pages_to_pdf(rgb_png_bytes: bytes) -> None:
    from src.image_convert import convert_image
    from src.config import CANVAS_A4

    img = convert_image(rgb_png_bytes, "a.png", canvas=CANVAS_A4, mode="fit")
    pdf = jpeg_pages_to_pdf([(img.data, img.width, img.height)])
    assert pdf.page_count == 1
    assert pdf.data.startswith(b"%PDF")


def test_rasterize_pdf(simple_pdf_bytes: bytes) -> None:
    result = convert_pdf_rasterize(simple_pdf_bytes, dpi=72)
    assert result.page_count == 1
    assert any("画像化" in w for w in result.warnings)


def test_rasterize_caps_dpi_by_page_product(monkeypatch: pytest.MonkeyPatch) -> None:
    import fitz

    monkeypatch.setattr("src.pdf_convert.MAX_RASTERIZE_PAGE_DPI_PRODUCT", 200)
    doc = fitz.open()
    for i in range(5):
        page = doc.new_page()
        page.insert_text((72, 72), str(i))
    data = doc.tobytes()
    doc.close()

    result = convert_pdf_rasterize(data, dpi=150)
    assert result.page_count == 5
    assert any("メモリ対策" in w for w in result.warnings)


def test_images_to_pdf_safe_inset(webp_bytes: bytes) -> None:
    from src.config import CANVAS_A4
    from src.pdf_convert import images_to_pdf

    result = images_to_pdf(
        [(webp_bytes, "a.webp")],
        canvas=CANVAS_A4,
        safe_inset=True,
    )
    assert result.page_count == 1
    assert any("セーフエリア" in w for w in result.warnings)
