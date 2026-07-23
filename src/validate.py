"""サービス適合チェック（domain.json の check_profiles / print_limits）."""

from __future__ import annotations

from dataclasses import dataclass

from .config import (
    MAX_FILE_BYTES,
    NW_MAX_PAGES_A4,
    NW_MIN_LONG_PX,
    NW_MIN_SHORT_PX,
    SEVEN_MAX_PAGES,
    SEVEN_PHOTO_MAX_SIDE,
    SEVEN_PHOTO_MIN_PX,
    SEVEN_PHOTO_RATIO_MAX,
    SEVEN_PHOTO_RATIO_MIN,
    Preset,
)
from .domain import load_domain

_CHECK_PROFILES = load_domain().check_profiles


@dataclass
class CheckItem:
    label: str
    ok: bool
    detail: str


def aspect_ratio(width: int, height: int) -> float:
    long_side = max(width, height)
    short_side = min(width, height)
    if short_side == 0:
        return 0.0
    return long_side / short_side


def _run_check(
    check_id: str,
    *,
    width: int,
    height: int,
    size_bytes: int,
    page_count: int | None = None,
) -> CheckItem | None:
    ratio = aspect_ratio(width, height)
    long_side, short_side = max(width, height), min(width, height)
    seven_min_long, seven_min_short = (
        max(SEVEN_PHOTO_MIN_PX),
        min(SEVEN_PHOTO_MIN_PX),
    )

    if check_id == "max_file_bytes":
        return CheckItem(
            label="容量 ≤10MB",
            ok=size_bytes <= MAX_FILE_BYTES,
            detail=f"{size_bytes / 1024 / 1024:.2f} MB",
        )
    if check_id == "nw_min_size":
        return CheckItem(
            label="最小サイズ目安（ネットワークプリント）",
            ok=long_side >= NW_MIN_LONG_PX and short_side >= NW_MIN_SHORT_PX,
            detail=f"{width}×{height}",
        )
    if check_id == "photo_ratio":
        in_ratio = SEVEN_PHOTO_RATIO_MIN <= ratio <= SEVEN_PHOTO_RATIO_MAX
        return CheckItem(
            label="フォト縦横比 1.3〜1.5",
            ok=in_ratio,
            detail=f"{ratio:.3f}",
        )
    if check_id == "square_ratio":
        # スクエア用紙向け（1:1 付近）
        in_ratio = 0.95 <= ratio <= 1.05
        return CheckItem(
            label="スクエア縦横比 ≈1.0",
            ok=in_ratio,
            detail=f"{ratio:.3f}",
        )
    if check_id == "max_side":
        return CheckItem(
            label="最大辺 ≤6144px",
            ok=long_side <= SEVEN_PHOTO_MAX_SIDE,
            detail=f"{width}×{height}",
        )
    if check_id == "seven_min_size":
        return CheckItem(
            label="最小サイズ目安（セブン）",
            ok=short_side >= seven_min_short and long_side >= seven_min_long,
            detail=f"{width}×{height}",
        )
    if check_id == "pdf_pages_ref":
        pages = page_count or 0
        return CheckItem(
            label="ページ数（参考）",
            ok=pages <= NW_MAX_PAGES_A4,
            detail=(
                f"{pages} ページ"
                f"（NW A4系≤{NW_MAX_PAGES_A4} / セブン≤{SEVEN_MAX_PAGES} 目安）"
            ),
        )
    return None


def validate_by_profile(
    check_profile: str,
    *,
    width: int = 0,
    height: int = 0,
    size_bytes: int,
    page_count: int | None = None,
) -> list[CheckItem]:
    profile = _CHECK_PROFILES.get(check_profile) or _CHECK_PROFILES.get("plain") or []
    checks: list[CheckItem] = []
    for check_id in profile:
        item = _run_check(
            check_id,
            width=width,
            height=height,
            size_bytes=size_bytes,
            page_count=page_count,
        )
        if item is not None:
            checks.append(item)
    return checks


def validate_image_result(
    width: int,
    height: int,
    size_bytes: int,
    preset: Preset,
    *,
    check_profile: str | None = None,
) -> list[CheckItem]:
    return validate_by_profile(
        check_profile or preset.check_profile,
        width=width,
        height=height,
        size_bytes=size_bytes,
    )


def validate_pdf_result(
    size_bytes: int,
    page_count: int,
    *,
    check_profile: str = "pdf",
) -> list[CheckItem]:
    return validate_by_profile(
        check_profile,
        size_bytes=size_bytes,
        page_count=page_count,
    )


def checks_all_ok(checks: list[CheckItem]) -> bool:
    return all(c.ok for c in checks)
