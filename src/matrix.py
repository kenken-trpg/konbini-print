"""出力の印刷選択肢適合マトリクス."""

from __future__ import annotations

from dataclasses import dataclass

from .validate import CheckItem, checks_all_ok, validate_by_profile

# 結果 × 印刷選択肢（ドメインの check_profile を再利用）
MATRIX_ROWS: tuple[tuple[str, str], ...] = (
    ("NW/セブン フォト L・2L", "photo"),
    ("NW スクエア", "square"),
    ("普通紙 A4 等", "plain"),
    ("はがき", "hagaki"),
    ("文書 PDF", "pdf"),
)


@dataclass(frozen=True)
class MatrixCell:
    option: str
    profile: str
    ok: bool
    detail: str
    checks: tuple[CheckItem, ...]


def compatibility_matrix(
    *,
    width: int = 0,
    height: int = 0,
    size_bytes: int,
    page_count: int | None = None,
    is_pdf: bool = False,
) -> list[MatrixCell]:
    """画像または PDF に対する選択肢ごとの OK/NG."""
    rows: list[MatrixCell] = []
    for label, profile in MATRIX_ROWS:
        if is_pdf and profile != "pdf":
            # 画像向けプロファイルは PDF には適用しない
            rows.append(
                MatrixCell(
                    option=label,
                    profile=profile,
                    ok=False,
                    detail="画像向け（PDF 非対象）",
                    checks=(),
                )
            )
            continue
        if not is_pdf and profile == "pdf":
            rows.append(
                MatrixCell(
                    option=label,
                    profile=profile,
                    ok=False,
                    detail="PDF 向け（画像非対象）",
                    checks=(),
                )
            )
            continue
        checks = validate_by_profile(
            profile,
            width=width,
            height=height,
            size_bytes=size_bytes,
            page_count=page_count,
        )
        ok = checks_all_ok(checks) if checks else False
        fail = next((c for c in checks if not c.ok), None)
        detail = "適合" if ok else (fail.detail if fail else "要確認")
        if not ok and fail:
            detail = f"{fail.label}: {fail.detail}"
        rows.append(
            MatrixCell(
                option=label,
                profile=profile,
                ok=ok,
                detail=detail,
                checks=tuple(checks),
            )
        )
    return rows


def matrix_as_table_rows(cells: list[MatrixCell]) -> list[dict[str, str]]:
    return [
        {
            "印刷選択肢": c.option,
            "判定": "OK" if c.ok else "NG",
            "詳細": c.detail,
        }
        for c in cells
    ]
