"""pipeline / dto 単体テスト."""

from src import BatchResult, InputFile, OutputArtifact, process_files
from src.config import PRESETS
from src.options import ProcessOptions
from src.ziputil import zip_artifacts


def test_process_image_preset_success(webp_bytes: bytes) -> None:
    batch = process_files(
        [InputFile("shot.webp", webp_bytes)],
        PRESETS["both_l"],
        options=ProcessOptions(fit_mode="fit"),
    )
    assert len(batch.outputs) == 1
    assert len(batch.errors) == 0
    art = batch.outputs[0]
    assert isinstance(art, OutputArtifact)
    assert art.is_image
    assert art.name.endswith(".jpg")
    assert art.targets
    assert art.data[:2] == b"\xff\xd8"


def test_process_continues_on_per_file_error(webp_bytes: bytes) -> None:
    batch = process_files(
        [
            InputFile("ok.webp", webp_bytes),
            InputFile("bad.heic", b"not-an-image"),
        ],
        PRESETS["both_l"],
        options=ProcessOptions(),
    )
    assert len(batch.outputs) == 1
    assert len(batch.errors) == 1
    assert "bad.heic" in batch.errors[0][0]


def test_both_all_pack_outputs_three_variants(webp_bytes: bytes) -> None:
    batch = process_files(
        [InputFile("p.webp", webp_bytes)],
        PRESETS["both_all"],
        options=ProcessOptions(),
    )
    assert len(batch.outputs) == 3
    names = " ".join(o.name for o in batch.outputs)
    assert "photo_L" in names
    assert "photo_2L" in names
    assert "plain_A4" in names


def test_image_preset_skips_pdf(simple_pdf_bytes: bytes, webp_bytes: bytes) -> None:
    batch = process_files(
        [
            InputFile("a.webp", webp_bytes),
            InputFile("doc.pdf", simple_pdf_bytes),
        ],
        PRESETS["both_l"],
        options=ProcessOptions(),
    )
    assert len(batch.outputs) == 1
    assert any("スキップ" in s or "pdf" in s.lower() for s in batch.skipped)


def test_pdf_compat_preset(simple_pdf_bytes: bytes) -> None:
    batch = process_files(
        [InputFile("doc.pdf", simple_pdf_bytes)],
        PRESETS["pdf_compat"],
        options=ProcessOptions(),
    )
    assert len(batch.outputs) == 1
    assert batch.outputs[0].is_pdf
    assert any("保証しません" in w for w in batch.outputs[0].warnings)


def test_zip_artifacts(webp_bytes: bytes) -> None:
    batch = process_files(
        [InputFile("a.webp", webp_bytes)],
        PRESETS["both_l"],
        options=ProcessOptions(),
    )
    z = zip_artifacts(batch.outputs)
    assert z[:2] == b"PK"


def test_batch_extend_errors() -> None:
    batch = BatchResult()
    batch.errors.append(("a", "1"))
    batch.extend_errors([("b", "2")])
    assert batch.errors == [("b", "2"), ("a", "1")]


def test_all_presets_have_pipeline() -> None:
    for pid, preset in PRESETS.items():
        assert preset.pipeline in {"image", "pdf", "images_to_pdf", "pack"}, pid
        if preset.pipeline == "pack":
            assert preset.variants


def test_images_to_pdf_pdf_only_no_false_error(simple_pdf_bytes: bytes) -> None:
    """画像なし・PDFのみでも「画像が必要」の誤エラーを出さない."""
    batch = process_files(
        [InputFile("doc.pdf", simple_pdf_bytes)],
        PRESETS["images_to_pdf"],
        options=ProcessOptions(),
    )
    assert len(batch.outputs) >= 1
    assert not any("画像ファイルが必要" in msg for _, msg in batch.errors)
