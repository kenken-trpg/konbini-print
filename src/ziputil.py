"""アーティファクトの ZIP 化（UI 非依存）."""

from __future__ import annotations

import io
import zipfile
from collections.abc import Iterable

from .dto import OutputArtifact
from .filenames import uniquify_arcname


def zip_artifacts(files: Iterable[OutputArtifact]) -> bytes:
    """出力を ZIP 化する。同名は stem_2.ext, stem_3.ext … に自動リネームする."""
    buf = io.BytesIO()
    used: set[str] = set()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for f in files:
            arcname = uniquify_arcname(f.name, used)
            zf.writestr(arcname, f.data)
    return buf.getvalue()
