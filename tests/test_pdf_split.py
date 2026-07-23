"""pdf split 単体テスト."""

from __future__ import annotations

import fitz
import pytest

from src import InputFile, process_files
from src.config import PRESETS
from src.options import ProcessOptions
from src.pdf_convert import split_pdf_by_pages


def _multipage_pdf(n: int) -> bytes:
    doc = fitz.open()
    for i in range(n):
        page = doc.new_page()
        page.insert_text((72, 72), f"page {i + 1}")
    data = doc.tobytes()
    doc.close()
    return data


def test_split_pdf_by_pages_chunks() -> None:
    data = _multipage_pdf(12)
    parts = split_pdf_by_pages(data, pages_per_file=5)
    assert len(parts) == 3
    assert [p.page_count for p in parts] == [5, 5, 2]
    assert all(p.data.startswith(b"%PDF") for p in parts)


def test_split_pdf_no_op_when_under_limit() -> None:
    data = _multipage_pdf(3)
    parts = split_pdf_by_pages(data, pages_per_file=50)
    assert len(parts) == 1
    assert parts[0].page_count == 3
    assert any("分割不要" in w for w in parts[0].warnings)


def test_split_pdf_rejects_invalid_pages() -> None:
    with pytest.raises(ValueError):
        split_pdf_by_pages(_multipage_pdf(2), pages_per_file=0)


def test_pipeline_split_user_option() -> None:
    data = _multipage_pdf(7)
    batch = process_files(
        [InputFile("long.pdf", data)],
        PRESETS["pdf_compat"],
        options=ProcessOptions(split_pdf=True, pages_per_file=3),
    )
    assert len(batch.errors) == 0
    assert len(batch.outputs) == 3
    assert all(o.is_pdf for o in batch.outputs)
    assert all("_p0" in o.name for o in batch.outputs)


def test_pipeline_pack_uses_variants_table(webp_bytes: bytes) -> None:
    preset = PRESETS["both_all"]
    assert preset.pipeline == "pack"
    assert len(preset.variants) == 3
    batch = process_files(
        [InputFile("x.webp", webp_bytes)],
        preset,
        options=ProcessOptions(),
    )
    assert len(batch.outputs) == 3
