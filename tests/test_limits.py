"""リソース上限の単体テスト."""

from __future__ import annotations

import io

import pytest
from PIL import Image

from src import InputFile, process_files
from src.config import PRESETS
from src.image_convert import load_image
from src.limits import ResourceLimitError, ensure_pdf_page_limit, validate_input_batch
from src.options import ProcessOptions
from src.pdf_convert import convert_pdf_compat


def test_validate_input_batch_file_count(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("src.limits.MAX_INPUT_FILES", 2)
    inputs = [InputFile(f"{i}.bin", b"x") for i in range(3)]
    with pytest.raises(ResourceLimitError, match="ファイル数"):
        validate_input_batch(inputs)


def test_validate_input_batch_total_bytes(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("src.limits.MAX_INPUT_TOTAL_BYTES", 10)
    with pytest.raises(ResourceLimitError, match="合計サイズ"):
        validate_input_batch([InputFile("a.bin", b"0123456789012345")])


def test_ensure_pdf_page_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("src.limits.MAX_PDF_PAGES", 5)
    with pytest.raises(ResourceLimitError, match="ページ数"):
        ensure_pdf_page_limit(6)


def test_load_image_rejects_over_pixel_cap(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("src.image_convert.MAX_IMAGE_PIXELS", 100)
    img = Image.new("RGB", (20, 20), (1, 2, 3))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    with pytest.raises(RuntimeError, match="ピクセル"):
        load_image(buf.getvalue(), "tiny.png")


def test_process_files_enforces_batch_limit(
    webp_bytes: bytes, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("src.limits.MAX_INPUT_FILES", 1)
    with pytest.raises(ResourceLimitError, match="ファイル数"):
        process_files(
            [
                InputFile("a.webp", webp_bytes),
                InputFile("b.webp", webp_bytes),
            ],
            PRESETS["both_l"],
            options=ProcessOptions(),
        )


def test_convert_pdf_compat_page_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    import fitz

    monkeypatch.setattr("src.limits.MAX_PDF_PAGES", 2)

    doc = fitz.open()
    for i in range(3):
        page = doc.new_page()
        page.insert_text((72, 72), str(i))
    data = doc.tobytes()
    doc.close()

    with pytest.raises(ResourceLimitError):
        convert_pdf_compat(data)


def test_would_exceed_input_total(monkeypatch: pytest.MonkeyPatch) -> None:
    from src.limits import would_exceed_input_total

    monkeypatch.setattr("src.limits.MAX_INPUT_TOTAL_BYTES", 100)
    assert not would_exceed_input_total(40, 50)
    assert would_exceed_input_total(40, 61)
    assert would_exceed_input_total(100, 1)
    assert not would_exceed_input_total(100, 0)
