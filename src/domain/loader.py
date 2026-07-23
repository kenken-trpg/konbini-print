"""domain.json ローダ（ドメイン知識の単一ソース）."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any, Literal

FitMode = Literal["fit", "crop"]
OutputKind = Literal["jpeg", "png", "pdf"]
PipelineKind = Literal["image", "pdf", "images_to_pdf", "pack"]
ServiceKind = Literal["seven", "network", "both"]
ContentKind = Literal["photo", "plain", "pdf", "pack"]

DOMAIN_JSON_PATH = Path(__file__).with_name("domain.json")


@dataclass(frozen=True)
class PresetVariant:
    """pack パイプライン用の1出力定義（自己完結）."""

    suffix: str
    canvas: tuple[int, int]
    kind: ContentKind
    check_profile: str
    targets: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class Preset:
    id: str
    label: str
    service: ServiceKind
    kind: ContentKind
    pipeline: PipelineKind
    canvas: tuple[int, int] | None
    output: OutputKind
    dpi: int = 300
    check_profile: str = "plain"
    targets: tuple[str, ...] = field(default_factory=tuple)
    variants: tuple[PresetVariant, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class ServiceLink:
    label: str
    url: str


@dataclass(frozen=True)
class PrintOptionLimit:
    option: str
    formats: str
    size_limit: str
    dimensions: str
    notes: str


@dataclass(frozen=True)
class DomainBundle:
    """ロード済みドメイン一式."""

    version: int
    verified_as_of: str
    raw: dict[str, Any]
    print_limits: dict[str, Any]
    resource_limits: dict[str, Any]
    canvases: dict[str, tuple[int, int]]
    check_profiles: dict[str, list[str]]
    presets: dict[str, Preset]
    preset_order: list[str]
    target_by_preset: dict[str, list[str]]
    service_labels: dict[str, str]
    service_specs: list[dict[str, Any]]
    pdf_compat_honest: str
    disclaimer_md: str
    pdf_split_page_choices: tuple[int, ...]
    image_extensions: set[str]
    pdf_extensions: set[str]


def _as_xy(value: list[int] | tuple[int, int]) -> tuple[int, int]:
    return (int(value[0]), int(value[1]))


def _resolve_canvas(
    key: str | list[int] | None, canvases: dict[str, tuple[int, int]]
) -> tuple[int, int] | None:
    if key is None:
        return None
    if isinstance(key, list):
        return _as_xy(key)
    return canvases[str(key)]


def _build_variant(
    raw: dict[str, Any], canvases: dict[str, tuple[int, int]]
) -> PresetVariant:
    canvas = _resolve_canvas(raw["canvas"], canvases)
    if canvas is None:
        raise ValueError(f"variant {raw.get('suffix')} に canvas が必要です")
    return PresetVariant(
        suffix=str(raw["suffix"]),
        canvas=canvas,
        kind=raw["kind"],
        check_profile=str(raw.get("check_profile", "plain")),
        targets=tuple(raw.get("targets") or ()),
    )


def _build_preset(
    raw: dict[str, Any], canvases: dict[str, tuple[int, int]]
) -> Preset:
    variants = tuple(
        _build_variant(v, canvases) for v in (raw.get("variants") or [])
    )
    return Preset(
        id=str(raw["id"]),
        label=str(raw["label"]),
        service=raw["service"],
        kind=raw["kind"],
        pipeline=raw["pipeline"],
        canvas=_resolve_canvas(raw.get("canvas"), canvases),
        output=raw["output"],
        dpi=int(raw.get("dpi", 300)),
        check_profile=str(raw.get("check_profile", "plain")),
        targets=tuple(raw.get("targets") or ()),
        variants=variants,
    )


def _build_service_spec(raw: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": raw.get("id"),
        "name": raw["name"],
        "links": [ServiceLink(**link) for link in raw.get("links", [])],
        "options": [PrintOptionLimit(**opt) for opt in raw.get("options", [])],
        "common": list(raw.get("common", [])),
    }


@lru_cache(maxsize=1)
def load_domain(path: str | None = None) -> DomainBundle:
    json_path = Path(path) if path else DOMAIN_JSON_PATH
    raw = json.loads(json_path.read_text(encoding="utf-8"))

    canvases = {k: _as_xy(v) for k, v in raw["canvases"].items()}
    presets_list = [_build_preset(p, canvases) for p in raw["presets"]]
    presets = {p.id: p for p in presets_list}
    target_by_preset = {p.id: list(p.targets) for p in presets_list}

    messages = raw.get("messages", {})
    extensions = raw.get("extensions", {})

    return DomainBundle(
        version=int(raw.get("version", 1)),
        verified_as_of=str(raw.get("verified_as_of", "")),
        raw=raw,
        print_limits=dict(raw["print_limits"]),
        resource_limits=dict(raw["resource_limits"]),
        canvases=canvases,
        check_profiles={
            k: list(v) for k, v in raw.get("check_profiles", {}).items()
        },
        presets=presets,
        preset_order=list(raw.get("preset_order", [p.id for p in presets_list])),
        target_by_preset=target_by_preset,
        service_labels=dict(raw.get("service_labels", {})),
        service_specs=[_build_service_spec(s) for s in raw.get("services", [])],
        pdf_compat_honest=str(messages.get("pdf_compat_honest", "")),
        disclaimer_md=str(messages.get("disclaimer_md", "")),
        pdf_split_page_choices=tuple(raw.get("pdf_split_page_choices", (10, 30, 50, 99))),
        image_extensions=set(extensions.get("image", [])),
        pdf_extensions=set(extensions.get("pdf", [".pdf"])),
    )


def get_preset(preset_id: str, bundle: DomainBundle | None = None) -> Preset:
    d = bundle or load_domain()
    try:
        return d.presets[preset_id]
    except KeyError as exc:
        raise KeyError(preset_id) from exc
