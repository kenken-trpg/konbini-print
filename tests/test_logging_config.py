"""logging_config 単体テスト."""

from __future__ import annotations

import logging
from pathlib import Path

from src.logging_config import get_logger, log_exception, setup_logging


def test_setup_logging_rotating_handler(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("KONBINI_LOG_DIR", str(tmp_path))
    monkeypatch.setenv("KONBINI_LOG_MAX_BYTES", "1024")
    monkeypatch.setenv("KONBINI_LOG_BACKUP_COUNT", "3")
    monkeypatch.setenv("KONBINI_LOG_LEVEL", "INFO")

    logger = setup_logging(force=True)
    assert logger.name == "konbini_print"

    rotating = [
        h
        for h in logger.handlers
        if h.__class__.__name__ == "RotatingFileHandler"
    ]
    assert len(rotating) == 1
    assert rotating[0].maxBytes == 1024
    assert rotating[0].backupCount == 3

    log_path = tmp_path / "konbini-print.log"
    logger.info("hello-log")
    for h in logger.handlers:
        h.flush()
    assert log_path.exists()
    assert "hello-log" in log_path.read_text(encoding="utf-8")


def test_log_exception_writes_traceback(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("KONBINI_LOG_DIR", str(tmp_path))
    setup_logging(force=True)

    try:
        raise ValueError("boom-test")
    except ValueError as exc:
        log_exception("unit-test-failure", exc, source="sample.bin")

    for h in get_logger().handlers:
        h.flush()

    text = (tmp_path / "konbini-print.log").read_text(encoding="utf-8")
    assert "unit-test-failure" in text
    assert "boom-test" in text
    assert "ValueError" in text
    assert "Traceback" in text


def test_log_exception_truncates_long_extra(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("KONBINI_LOG_DIR", str(tmp_path))
    setup_logging(force=True)
    try:
        raise RuntimeError("x")
    except RuntimeError as exc:
        log_exception("trunc", exc, extra={"blob": "a" * 500})

    for h in get_logger().handlers:
        h.flush()
    text = (tmp_path / "konbini-print.log").read_text(encoding="utf-8")
    assert "…" in text
    assert "a" * 500 not in text
