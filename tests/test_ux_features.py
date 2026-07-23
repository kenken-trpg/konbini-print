"""precheck / matrix / safe preview のテスト."""

from __future__ import annotations

import io

from PIL import Image

from src import InputFile, process_files
from src.config import PRESETS
from src.image_convert import apply_safe_inset, convert_image
from src.matrix import compatibility_matrix
from src.options import ProcessOptions
from src.precheck import probe_input
from src.preview import add_safe_area_guide, make_image_thumbnail


def test_probe_image(webp_bytes: bytes) -> None:
    p = probe_input(InputFile("テスト.webp", webp_bytes))
    assert p.kind == "image"
    assert p.width and p.height
    assert p.sanitized_stem == "テスト"
    assert not p.name_will_change


def test_probe_pdf(simple_pdf_bytes: bytes) -> None:
    p = probe_input(InputFile("doc.pdf", simple_pdf_bytes))
    assert p.kind == "pdf"
    assert p.page_count == 1


def test_compatibility_matrix_photo_l_ok() -> None:
    cells = compatibility_matrix(width=1500, height=1051, size_bytes=100_000)
    by_opt = {c.option: c for c in cells}
    assert by_opt["NW/セブン フォト L・2L"].ok
    assert not by_opt["NW スクエア"].ok
    assert not by_opt["文書 PDF"].ok


def test_compatibility_matrix_pdf() -> None:
    cells = compatibility_matrix(size_bytes=1000, page_count=3, is_pdf=True)
    by_opt = {c.option: c for c in cells}
    assert by_opt["文書 PDF"].ok
    assert not by_opt["普通紙 A4 等"].ok


def test_safe_inset_shrinks_content() -> None:
    img = Image.new("RGB", (100, 100), (0, 128, 255))
    out = apply_safe_inset(img, inset_ratio=0.1, bg=(255, 255, 255))
    assert out.size == (100, 100)
    # 四隅は背景色に近い
    assert out.getpixel((0, 0)) == (255, 255, 255)


def test_safe_inset_via_convert(webp_bytes: bytes) -> None:
    r = convert_image(
        webp_bytes,
        "a.webp",
        canvas=(500, 500),
        safe_inset=True,
        safe_inset_ratio=0.05,
    )
    assert any("セーフエリア" in w for w in r.warnings)


def test_safe_area_guide_bytes(rgb_png_bytes: bytes) -> None:
    thumb = make_image_thumbnail(rgb_png_bytes)
    guided = add_safe_area_guide(thumb)
    assert guided[:2] == b"\xff\xd8"
    assert len(guided) > 0


def test_japanese_output_name_kept(webp_bytes: bytes) -> None:
    batch = process_files(
        [InputFile("夏休みの写真.webp", webp_bytes)],
        PRESETS["both_l"],
        options=ProcessOptions(),
    )
    assert len(batch.outputs) == 1
    assert "夏休みの写真" in batch.outputs[0].name
    assert batch.outputs[0].source_name == "夏休みの写真.webp"
