"""client/domain.json と本線 src/domain/domain.json のドリフト検知.

スパイクブランチ専用の契約テスト。master に client/ が無い場合はスキップする。
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
MAIN_DOMAIN = ROOT / "src" / "domain" / "domain.json"
CLIENT_DOMAIN = ROOT / "client" / "domain.json"


@pytest.mark.skipif(not CLIENT_DOMAIN.is_file(), reason="client/ が無い（本線のみ）")
def test_client_domain_json_matches_mainline() -> None:
    main = json.loads(MAIN_DOMAIN.read_text(encoding="utf-8"))
    client = json.loads(CLIENT_DOMAIN.read_text(encoding="utf-8"))
    assert client == main, (
        "client/domain.json が本線と異なります。"
        " src/domain/domain.json を client/ へコピーしてください。"
    )
