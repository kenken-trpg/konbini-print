"""I/O 層: URL 取得・ZIP・ファイル名・実体検知・ログ.

変換ロジックは持たない。``src.convert`` / ``src.domain`` から利用される。
"""

from ..content_sniff import ContentTypeError, sniff_kind, validate_and_normalize_name
from ..fetch_url import FetchedFile, UrlFetchError, fetch_public_url, parse_url_list, redact_url_for_log
from ..filenames import SEVEN_FILENAME_CAUTION, sanitize_filename, sanitize_stem, uniquify_arcname
from ..logging_config import get_logger, log_exception, setup_logging
from ..ziputil import zip_artifacts

__all__ = [
    "ContentTypeError",
    "FetchedFile",
    "SEVEN_FILENAME_CAUTION",
    "UrlFetchError",
    "fetch_public_url",
    "get_logger",
    "log_exception",
    "parse_url_list",
    "redact_url_for_log",
    "sanitize_filename",
    "sanitize_stem",
    "setup_logging",
    "sniff_kind",
    "uniquify_arcname",
    "validate_and_normalize_name",
    "zip_artifacts",
]
