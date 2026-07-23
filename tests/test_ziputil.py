"""ZIP 化の単体テスト."""

from __future__ import annotations

import io
import zipfile

from src.dto import OutputArtifact
from src.filenames import uniquify_arcname
from src.ziputil import zip_artifacts


def test_uniquify_arcname() -> None:
    used: set[str] = set()
    assert uniquify_arcname("a.jpg", used) == "a.jpg"
    assert uniquify_arcname("a.jpg", used) == "a_2.jpg"
    assert uniquify_arcname("a.jpg", used) == "a_3.jpg"
    assert uniquify_arcname("a_2.jpg", used) == "a_2_2.jpg"


def test_zip_artifacts_dedupes_names() -> None:
    files = [
        OutputArtifact(name="same.jpg", data=b"one", mime="image/jpeg", meta=""),
        OutputArtifact(name="same.jpg", data=b"two", mime="image/jpeg", meta=""),
        OutputArtifact(name="other.png", data=b"png", mime="image/png", meta=""),
    ]
    raw = zip_artifacts(files)
    with zipfile.ZipFile(io.BytesIO(raw)) as zf:
        names = zf.namelist()
        assert names == ["same.jpg", "same_2.jpg", "other.png"]
        assert zf.read("same.jpg") == b"one"
        assert zf.read("same_2.jpg") == b"two"
