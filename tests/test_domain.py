"""domain.json 単一ソースの整合性テスト."""

from __future__ import annotations

import pytest

from src.config import PRESET_ORDER, PRESETS, get_preset
from src.domain import DOMAIN_JSON_PATH, load_domain
from src.targets import TARGET_BY_PRESET
from src.validate import validate_image_result


def test_domain_json_exists() -> None:
    assert DOMAIN_JSON_PATH.is_file()


def test_presets_match_order_and_targets() -> None:
    domain = load_domain()
    assert set(PRESETS) == set(domain.presets)
    assert PRESET_ORDER == domain.preset_order
    for pid in PRESET_ORDER:
        assert pid in PRESETS
        assert list(PRESETS[pid].targets) == TARGET_BY_PRESET[pid]


def test_pack_variants_are_self_contained() -> None:
    pack = PRESETS["both_all"]
    assert pack.pipeline == "pack"
    assert len(pack.variants) == 3
    for v in pack.variants:
        assert v.canvas[0] > 0 and v.canvas[1] > 0
        assert v.check_profile in {"photo", "plain"}
        assert v.targets
        # 旧 validate_preset_id 依存は廃止
        assert not hasattr(v, "validate_preset_id")


def test_get_preset() -> None:
    assert get_preset("both_l").id == "both_l"
    with pytest.raises(KeyError):
        get_preset("plain_a4")


def test_validate_uses_check_profile() -> None:
    photo = PRESETS["both_l"]
    checks = validate_image_result(1500, 1051, 100_000, photo)
    labels = [c.label for c in checks]
    assert "容量 ≤10MB" in labels
    assert "フォト縦横比 1.3〜1.5" in labels

    plain = PRESETS["both_plain_a4"]
    plain_checks = validate_image_result(1654, 2339, 100_000, plain)
    plain_labels = [c.label for c in plain_checks]
    assert "フォト縦横比 1.3〜1.5" not in plain_labels
