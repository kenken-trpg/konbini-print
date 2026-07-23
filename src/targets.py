"""結果が想定する印刷向き先ラベル（domain.json）."""

from __future__ import annotations

from .domain import load_domain

_domain = load_domain()

TARGET_BY_PRESET: dict[str, list[str]] = dict(_domain.target_by_preset)
PDF_COMPAT_HONEST = _domain.pdf_compat_honest
