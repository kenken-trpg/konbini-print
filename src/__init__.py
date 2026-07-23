"""コンビニプリント変換コア（Streamlit 非依存）.

公開 API（推奨の入口）:

```python
from src import (
    InputFile,
    OutputArtifact,
    BatchResult,
    ProcessOptions,
    process_files,
    PRESETS,
    load_domain,
    setup_logging,
)
```

層分け:
- ``src.domain`` … ドメイン知識（domain.json / プリセット / 制限 / 検証）
- ``src.convert`` … 変換（画像・PDF・pipeline）
- ``src.io`` … 入出力（URL 取得・ZIP・ファイル名・ログ）
"""

from .config import PRESET_ORDER, PRESETS
from .domain import DOMAIN_JSON_PATH, Preset, PresetVariant, get_preset, load_domain
from .dto import BatchResult, InputFile, OutputArtifact
from .logging_config import get_logger, log_exception, setup_logging
from .options import ProcessOptions
from .pipeline import process_files

__all__ = [
    "BatchResult",
    "DOMAIN_JSON_PATH",
    "InputFile",
    "OutputArtifact",
    "PRESETS",
    "PRESET_ORDER",
    "Preset",
    "PresetVariant",
    "ProcessOptions",
    "get_logger",
    "get_preset",
    "load_domain",
    "log_exception",
    "process_files",
    "setup_logging",
]
