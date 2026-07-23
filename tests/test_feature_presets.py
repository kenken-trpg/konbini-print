"""スクエア・はがき・パック出力選択のテスト."""

from __future__ import annotations

import io

from PIL import Image

from src import InputFile, process_files
from src.config import CANVAS_HAGAKI, CANVAS_SQUARE, PRESETS
from src.options import ProcessOptions
from src.validate import validate_image_result


def test_nw_square_preset(webp_bytes: bytes) -> None:
    batch = process_files(
        [InputFile("a.webp", webp_bytes)],
        PRESETS["nw_square"],
        options=ProcessOptions(),
    )
    assert len(batch.errors) == 0
    assert len(batch.outputs) == 1
    art = batch.outputs[0]
    img = Image.open(io.BytesIO(art.data))
    assert img.size == (CANVAS_SQUARE[0], CANVAS_SQUARE[1])
    assert any("スクエア" in t for t in art.targets)
    assert any(c.label.startswith("スクエア縦横比") and c.ok for c in art.checks)


def test_both_hagaki_preset(webp_bytes: bytes) -> None:
    batch = process_files(
        [InputFile("a.webp", webp_bytes)],
        PRESETS["both_hagaki"],
        options=ProcessOptions(),
    )
    assert len(batch.errors) == 0
    out = batch.outputs[0]
    img = Image.open(io.BytesIO(out.data))
    assert set(img.size) == set(CANVAS_HAGAKI)
    assert any("はがき" in t for t in out.targets)


def test_pack_variant_filter(webp_bytes: bytes) -> None:
    batch = process_files(
        [InputFile("a.webp", webp_bytes)],
        PRESETS["both_all"],
        options=ProcessOptions(pack_variant_suffixes=("photo_L", "plain_A4")),
    )
    assert len(batch.errors) == 0
    assert len(batch.outputs) == 2
    names = " ".join(o.name for o in batch.outputs)
    assert "photo_L" in names
    assert "plain_A4" in names
    assert "photo_2L" not in names


def test_pack_variant_none_selected_errors(webp_bytes: bytes) -> None:
    batch = process_files(
        [InputFile("a.webp", webp_bytes)],
        PRESETS["both_all"],
        options=ProcessOptions(pack_variant_suffixes=()),
    )
    assert len(batch.outputs) == 0
    assert any("バリアント" in msg for _, msg in batch.errors)


def test_square_check_profile_rejects_l_ratio() -> None:
    checks = validate_image_result(
        1500,
        1051,
        100_000,
        PRESETS["nw_square"],
    )
    ratio_check = next(c for c in checks if "スクエア" in c.label)
    assert not ratio_check.ok
