"""content_sniff / セッション上限のテスト."""

from __future__ import annotations

import pytest

from src import InputFile, process_files
from src.config import PRESETS
from src.content_sniff import ContentTypeError, sniff_kind, validate_and_normalize_name
from src.limits import ResourceLimitError, normalize_input_files, session_result_within_limits
from src.options import ProcessOptions


def test_sniff_jpeg_png_pdf(rgb_png_bytes: bytes, simple_pdf_bytes: bytes) -> None:
    assert sniff_kind(rgb_png_bytes) == "png"
    assert sniff_kind(simple_pdf_bytes) == "pdf"
    assert sniff_kind(b"not-a-file") is None


def test_reject_extension_spoof_png_as_jpg(rgb_png_bytes: bytes) -> None:
    with pytest.raises(ContentTypeError, match="一致しません"):
        validate_and_normalize_name("fake.jpg", rgb_png_bytes)


def test_normalize_adds_extension(rgb_png_bytes: bytes) -> None:
    name, kind = validate_and_normalize_name("photo", rgb_png_bytes)
    assert kind == "png"
    assert name.endswith(".png")


def test_pipeline_rejects_spoof(rgb_png_bytes: bytes) -> None:
    batch = process_files(
        [InputFile("spoof.jpg", rgb_png_bytes)],
        PRESETS["both_l"],
        options=ProcessOptions(),
    )
    assert len(batch.outputs) == 0
    assert len(batch.errors) == 1
    assert "拡張子" in batch.errors[0][1]


def test_normalize_input_files_ok(webp_bytes: bytes) -> None:
    out, errors = normalize_input_files([InputFile("a.webp", webp_bytes)])
    assert not errors
    assert out[0].name.endswith(".webp")


def test_session_result_within_limits(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("src.limits.MAX_SESSION_OUTPUTS", 2)
    monkeypatch.setattr("src.limits.MAX_SESSION_RESULT_BYTES", 100)
    assert session_result_within_limits(1, 50)
    assert not session_result_within_limits(3, 10)
    assert not session_result_within_limits(1, 200)
