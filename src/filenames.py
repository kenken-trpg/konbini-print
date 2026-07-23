"""ファイル名サニタイズ.

方針:
- 日本語など文字はそのまま残す
- 記号もできるだけ残す
- OS / パスとして危険な文字だけ置換（\\ / : * ? \" < > | と制御文字）
- セブンネットプリントは公式に「記号・絵文字で失敗することがある」と明記しているため、
  絵文字は除去し、UI でも注意を出す（強制 ASCII 化はしない）
"""

from __future__ import annotations

import re
import unicodedata
from pathlib import Path


# パス・OS 的に危険（Windows / ZIP / URL でも問題になりやすい）
_PATH_UNSAFE = re.compile(r'[\\/:*?"<>|]')
_MULTI_UNDERSCORE = re.compile(r"_+")
# 簡易絵文字レンジ（セブン公式が絵文字失敗を明記）
_EMOJI = re.compile(
    "["
    "\U0001F300-\U0001F9FF"  # Misc Symbols and Pictographs 等
    "\U0001FA00-\U0001FAFF"
    "\U00002700-\U000027BF"  # Dingbats
    "\U00002600-\U000026FF"  # Misc symbols
    "\U0000FE00-\U0000FE0F"  # variation selectors
    "\U0000200D"  # ZWJ
    "]+",
    flags=re.UNICODE,
)

SEVEN_FILENAME_CAUTION = (
    "セブンネットプリントは公式に、ファイル名の記号・絵文字で失敗することがあると記載しています。"
)


def sanitize_stem(name: str, fallback: str = "file") -> str:
    """拡張子なしの名前をサニタイズする（日本語・多くの記号は維持）."""
    stem = Path(name).stem
    stem = unicodedata.normalize("NFKC", stem)
    # 制御文字を除去
    stem = "".join(ch for ch in stem if unicodedata.category(ch) != "Cc")
    stem = _PATH_UNSAFE.sub("_", stem)
    stem = _EMOJI.sub("", stem)
    stem = _MULTI_UNDERSCORE.sub("_", stem).strip(" ._")
    if not stem:
        stem = fallback
    return stem[:80]


def sanitize_filename(name: str, new_ext: str, index: int | None = None) -> str:
    stem = sanitize_stem(name)
    if index is not None:
        stem = f"{stem}_{index:03d}"
    ext = new_ext if new_ext.startswith(".") else f".{new_ext}"
    return f"{stem}{ext.lower()}"


def filename_changed(original: str, sanitized: str) -> bool:
    """拡張子を除いた表示用比較."""
    return Path(original).stem != Path(sanitized).stem


def uniquify_arcname(name: str, used: set[str]) -> str:
    """ZIP 内などで重複しないアーカイブ名を返す（used を更新する）."""
    base = name or "file.bin"
    if base not in used:
        used.add(base)
        return base
    path = Path(base)
    stem = path.stem or "file"
    ext = path.suffix
    n = 2
    while True:
        candidate = f"{stem}_{n}{ext}"
        if candidate not in used:
            used.add(candidate)
            return candidate
        n += 1
