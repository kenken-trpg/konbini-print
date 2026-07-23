"""アプリケーションログ設定（ローテーション付き）.

肥大化対策:
- RotatingFileHandler（サイズベース）
- 既定: 1ファイル最大 2MB × 世代 5 = 合計おおよそ 10MB 前後
- 環境変数で調整可能

環境変数:
- KONBINI_LOG_DIR: ログディレクトリ（既定: logs）
- KONBINI_LOG_MAX_BYTES: 1ファイル上限バイト（既定: 2097152 = 2MB）
- KONBINI_LOG_BACKUP_COUNT: 世代数（既定: 5）
- KONBINI_LOG_LEVEL: DEBUG/INFO/WARNING/ERROR（既定: INFO）
"""

from __future__ import annotations

import logging
import os
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

LOGGER_NAME = "konbini_print"

_DEFAULT_MAX_BYTES = 2 * 1024 * 1024  # 2MB
_DEFAULT_BACKUP_COUNT = 5
_configured = False


def _env_int(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        value = int(raw)
        return value if value > 0 else default
    except ValueError:
        return default


def log_dir() -> Path:
    return Path(os.environ.get("KONBINI_LOG_DIR", "logs"))


def setup_logging(*, force: bool = False) -> logging.Logger:
    """ロガーを初期化する（多重設定を防ぐ）."""
    global _configured
    logger = logging.getLogger(LOGGER_NAME)

    if _configured and not force:
        return logger

    if force:
        logger.handlers.clear()
        _configured = False

    level_name = os.environ.get("KONBINI_LOG_LEVEL", "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)
    logger.setLevel(level)
    logger.propagate = False

    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # コンソール: WARNING 以上（Streamlit 出力を汚しすぎない）
    console = logging.StreamHandler(sys.stderr)
    console.setLevel(logging.WARNING)
    console.setFormatter(formatter)
    logger.addHandler(console)

    # ファイル: ローテーション
    directory = log_dir()
    try:
        directory.mkdir(parents=True, exist_ok=True)
        max_bytes = _env_int("KONBINI_LOG_MAX_BYTES", _DEFAULT_MAX_BYTES)
        backup_count = _env_int("KONBINI_LOG_BACKUP_COUNT", _DEFAULT_BACKUP_COUNT)
        file_handler = RotatingFileHandler(
            directory / "konbini-print.log",
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding="utf-8",
        )
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    except OSError as exc:
        # Cloud 等で書き込み不可でもアプリは継続
        console.setLevel(logging.INFO)
        logger.warning("ログファイルを開けませんでした（コンソールのみ）: %s", exc)

    _configured = True
    logger.debug(
        "logging ready dir=%s maxBytes=%s backupCount=%s",
        directory,
        _env_int("KONBINI_LOG_MAX_BYTES", _DEFAULT_MAX_BYTES),
        _env_int("KONBINI_LOG_BACKUP_COUNT", _DEFAULT_BACKUP_COUNT),
    )
    return logger


def get_logger() -> logging.Logger:
    """設定済みロガーを返す（未設定なら初期化）."""
    if not _configured:
        return setup_logging()
    return logging.getLogger(LOGGER_NAME)


def log_exception(
    message: str,
    exc: BaseException,
    *,
    source: str | None = None,
    extra: dict | None = None,
) -> None:
    """例外を ERROR + traceback で記録する（ファイル肥大化を抑えるためメッセージは短く）.

    ファイル本体やバイナリは記録しない。
    """
    logger = get_logger()
    parts = [message]
    if source:
        parts.append(f"source={source!s}")
    parts.append(f"exc_type={type(exc).__name__}")
    parts.append(f"exc={exc!s}")
    if extra:
        for key, value in extra.items():
            # 値は短く
            text = str(value)
            if len(text) > 200:
                text = text[:200] + "…"
            parts.append(f"{key}={text}")
    logger.error(" | ".join(parts), exc_info=(type(exc), exc, exc.__traceback__))
