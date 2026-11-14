"""filenames 単体テスト."""

import pytest

from src.config import MAX_FILENAME_CHARS
from src.filenames import (
    SEVEN_FILENAME_CAUTION,
    build_filename,
    filename_changed,
    fit_filename,
    sanitize_filename,
    sanitize_stem,
    uniquify_arcname,
)


def test_sanitize_stem_removes_path_unsafe_only() -> None:
    assert sanitize_stem("b:c*d?.jpg") == "b_c_d"
    assert sanitize_stem("path/photo.jpg") == "photo"


def test_sanitize_stem_keeps_japanese() -> None:
    assert sanitize_stem("写真アルバム.jpg") == "写真アルバム"
    assert sanitize_stem("photo写真.jpg") == "photo写真"


def test_sanitize_stem_keeps_common_symbols() -> None:
    # NFKC で全角！は半角! になる
    assert sanitize_stem("夏の思い出！(最終).jpg") == "夏の思い出!(最終)"
    assert sanitize_stem("My Photo!.PNG") == "My Photo!"


def test_sanitize_stem_strips_emoji_for_seven() -> None:
    assert sanitize_stem("写真🎉.jpg") == "写真"
    assert "絵文字" in SEVEN_FILENAME_CAUTION


def test_sanitize_stem_empty_fallback() -> None:
    assert sanitize_stem("???.png", fallback="photo") == "photo"
    assert sanitize_stem("🎉🎉.png", fallback="photo") == "photo"


def test_sanitize_stem_truncates() -> None:
    long_name = "あ" * 100 + ".jpg"
    assert len(sanitize_stem(long_name)) <= 80
    assert "あ" in sanitize_stem(long_name)


def test_sanitize_filename_with_index_and_ext() -> None:
    assert sanitize_filename("My Photo!.PNG", ".jpg", index=2) == "My Photo!_002.jpg"


def test_sanitize_filename_ext_without_dot() -> None:
    assert sanitize_filename("x", "PDF") == "x.pdf"


def test_filename_changed() -> None:
    assert filename_changed("a:b.jpg", "a_b")
    assert not filename_changed("写真.jpg", "写真")


def test_max_filename_chars_is_network_print_limit() -> None:
    # ネットワークプリントは 100 文字超でアップロード失敗
    assert MAX_FILENAME_CHARS == 100


def test_build_filename_keeps_suffix_and_ext_when_trimming() -> None:
    name = build_filename("あ" * 200, "_001_plain_A4", ".jpg")
    assert len(name) == MAX_FILENAME_CHARS
    assert name.endswith("_001_plain_A4.jpg")


def test_build_filename_short_name_unchanged() -> None:
    assert build_filename("写真", "_001", ".jpg") == "写真_001.jpg"


def test_build_filename_counts_code_points() -> None:
    # サロゲートペアになる拡張漢字も 1 文字として数え、途中で切らない
    name = build_filename("𠮷" * 200, "_001", ".jpg")
    assert len(name) == MAX_FILENAME_CHARS
    assert name == "𠮷" * (MAX_FILENAME_CHARS - 8) + "_001.jpg"


def test_build_filename_strips_trailing_separator_after_trim() -> None:
    name = build_filename("a" * 5 + " " * 10, "_1", ".jpg", max_chars=12)
    assert name == "aaaaa_1.jpg"


def test_build_filename_rejects_impossible_budget() -> None:
    with pytest.raises(ValueError):
        build_filename("a", "_" * 10, ".jpg", max_chars=12)


def test_sanitize_filename_within_limit_for_large_index() -> None:
    name = sanitize_filename("あ" * 300 + ".png", ".jpeg", index=12345)
    assert len(name) <= MAX_FILENAME_CHARS
    assert name.endswith("_12345.jpeg")


def test_fit_filename_keeps_extension() -> None:
    name = fit_filename("x" * 150 + ".pdf")
    assert len(name) == MAX_FILENAME_CHARS
    assert name.endswith(".pdf")
    assert fit_filename("short.pdf") == "short.pdf"


def test_uniquify_arcname_stays_within_limit() -> None:
    used: set[str] = set()
    long_name = "あ" * (MAX_FILENAME_CHARS - 4) + ".jpg"  # ちょうど 100 文字
    first = uniquify_arcname(long_name, used)
    second = uniquify_arcname(long_name, used)
    third = uniquify_arcname(long_name, used)
    assert first == long_name
    assert len({first, second, third}) == 3
    for n in (second, third):
        assert len(n) <= MAX_FILENAME_CHARS
        assert n.endswith(".jpg")
    assert second.endswith("_2.jpg")
    assert third.endswith("_3.jpg")
