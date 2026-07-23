"""ドメイン層: 印刷仕様・プリセット・制限・適合チェック.

単一ソースは ``domain.json``（``loader``）。
他モジュールからの同期 import 循環を避けるため、便利な再エクスポートは遅延解決する。
"""

from __future__ import annotations

from typing import Any

from .loader import (
    DOMAIN_JSON_PATH,
    ContentKind,
    DomainBundle,
    FitMode,
    OutputKind,
    PipelineKind,
    Preset,
    PresetVariant,
    PrintOptionLimit,
    ServiceKind,
    ServiceLink,
    get_preset,
    load_domain,
)

__all__ = [
    "ALLOW_URL_FETCH",
    "CANVAS_2L",
    "CANVAS_A4",
    "CANVAS_HAGAKI",
    "CANVAS_L",
    "CANVAS_SQUARE",
    "CheckItem",
    "ContentKind",
    "DISCLAIMER_MD",
    "DOMAIN_JSON_PATH",
    "DOMAIN_VERIFIED_AS_OF",
    "DomainBundle",
    "FitMode",
    "MAX_DOWNLOAD_BYTES",
    "MAX_FILE_BYTES",
    "MAX_INPUT_FILES",
    "MAX_INPUT_TOTAL_BYTES",
    "MAX_SESSION_OUTPUTS",
    "MAX_SESSION_RESULT_BYTES",
    "OutputKind",
    "PDF_COMPAT_HONEST",
    "PRESETS",
    "PRESET_ORDER",
    "PipelineKind",
    "Preset",
    "PresetVariant",
    "PrintOptionLimit",
    "ResourceLimitError",
    "SERVICE_LABELS",
    "SERVICE_SPECS",
    "ServiceKind",
    "ServiceLink",
    "TARGET_BY_PRESET",
    "checks_all_ok",
    "get_preset",
    "load_domain",
    "validate_by_profile",
    "validate_image_result",
    "validate_input_batch",
    "validate_pdf_result",
]

_LAZY: dict[str, tuple[str, str]] = {
    "PRESETS": ("src.config", "PRESETS"),
    "PRESET_ORDER": ("src.config", "PRESET_ORDER"),
    "SERVICE_LABELS": ("src.config", "SERVICE_LABELS"),
    "MAX_FILE_BYTES": ("src.config", "MAX_FILE_BYTES"),
    "CANVAS_L": ("src.config", "CANVAS_L"),
    "CANVAS_2L": ("src.config", "CANVAS_2L"),
    "CANVAS_A4": ("src.config", "CANVAS_A4"),
    "CANVAS_SQUARE": ("src.config", "CANVAS_SQUARE"),
    "CANVAS_HAGAKI": ("src.config", "CANVAS_HAGAKI"),
    "ALLOW_URL_FETCH": ("src.limits", "ALLOW_URL_FETCH"),
    "MAX_DOWNLOAD_BYTES": ("src.limits", "MAX_DOWNLOAD_BYTES"),
    "MAX_INPUT_FILES": ("src.limits", "MAX_INPUT_FILES"),
    "MAX_INPUT_TOTAL_BYTES": ("src.limits", "MAX_INPUT_TOTAL_BYTES"),
    "MAX_SESSION_OUTPUTS": ("src.limits", "MAX_SESSION_OUTPUTS"),
    "MAX_SESSION_RESULT_BYTES": ("src.limits", "MAX_SESSION_RESULT_BYTES"),
    "ResourceLimitError": ("src.limits", "ResourceLimitError"),
    "validate_input_batch": ("src.limits", "validate_input_batch"),
    "DISCLAIMER_MD": ("src.service_info", "DISCLAIMER_MD"),
    "DOMAIN_VERIFIED_AS_OF": ("src.service_info", "DOMAIN_VERIFIED_AS_OF"),
    "SERVICE_SPECS": ("src.service_info", "SERVICE_SPECS"),
    "PDF_COMPAT_HONEST": ("src.targets", "PDF_COMPAT_HONEST"),
    "TARGET_BY_PRESET": ("src.targets", "TARGET_BY_PRESET"),
    "CheckItem": ("src.validate", "CheckItem"),
    "checks_all_ok": ("src.validate", "checks_all_ok"),
    "validate_by_profile": ("src.validate", "validate_by_profile"),
    "validate_image_result": ("src.validate", "validate_image_result"),
    "validate_pdf_result": ("src.validate", "validate_pdf_result"),
}


def __getattr__(name: str) -> Any:
    if name in _LAZY:
        import importlib

        mod_name, attr = _LAZY[name]
        mod = importlib.import_module(mod_name)
        value = getattr(mod, attr)
        globals()[name] = value
        return value
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
