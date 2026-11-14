"""client/domain.json と本線 src/domain/domain.json のドリフト検知.

Streamlit 版とブラウザ版を同じリポジトリで並行維持するための契約テスト。
正本は src/domain/domain.json。
"""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MAIN_DOMAIN = ROOT / "src" / "domain" / "domain.json"
CLIENT_DOMAIN = ROOT / "client" / "domain.json"


def test_client_domain_json_matches_mainline() -> None:
    main = json.loads(MAIN_DOMAIN.read_text(encoding="utf-8"))
    client = json.loads(CLIENT_DOMAIN.read_text(encoding="utf-8"))
    assert client == main, (
        "client/domain.json が本線と異なります。"
        " src/domain/domain.json を client/ へコピーしてください。"
    )
