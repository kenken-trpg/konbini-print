"""filenames 単体テスト."""

from src.filenames import (
    SEVEN_FILENAME_CAUTION,
    filename_changed,
    sanitize_filename,
    sanitize_stem,
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
