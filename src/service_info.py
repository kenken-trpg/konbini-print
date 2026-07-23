"""公式サービス情報・印刷選択肢ごとの制限（domain.json）."""

from __future__ import annotations

from .domain import PrintOptionLimit, ServiceLink, load_domain

_domain = load_domain()

SERVICE_SPECS = list(_domain.service_specs)
DISCLAIMER_MD = _domain.disclaimer_md
DOMAIN_VERIFIED_AS_OF = _domain.verified_as_of

__all__ = [
    "DISCLAIMER_MD",
    "DOMAIN_VERIFIED_AS_OF",
    "PrintOptionLimit",
    "SERVICE_SPECS",
    "ServiceLink",
]
