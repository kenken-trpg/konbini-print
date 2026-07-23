"""validate 単体テスト."""

import pytest

from src.config import PRESETS
from src.validate import (
    aspect_ratio,
    checks_all_ok,
    validate_image_result,
    validate_pdf_result,
)


def test_aspect_ratio() -> None:
    assert aspect_ratio(1500, 1051) == pytest.approx(1.427, rel=1e-3)
    assert aspect_ratio(0, 10) == 0.0


def test_photo_preset_checks_pass_for_l_canvas() -> None:
    preset = PRESETS["both_l"]
    checks = validate_image_result(1500, 1051, 100_000, preset)
    assert checks_all_ok(checks)


def test_photo_ratio_fails_for_square() -> None:
    preset = PRESETS["both_l"]
    checks = validate_image_result(1000, 1000, 1000, preset)
    ratio_check = next(c for c in checks if "縦横比" in c.label)
    assert ratio_check.ok is False


def test_size_over_10mb_fails() -> None:
    preset = PRESETS["both_safe"]
    checks = validate_image_result(800, 600, 11 * 1024 * 1024, preset)
    size_check = next(c for c in checks if "10MB" in c.label)
    assert size_check.ok is False


def test_pdf_page_check() -> None:
    checks = validate_pdf_result(1000, 51)
    page_check = next(c for c in checks if "ページ" in c.label)
    assert page_check.ok is False
    assert checks_all_ok(validate_pdf_result(1000, 10))
