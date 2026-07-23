"""公開 API と層パッケージの import スモークテスト."""

from __future__ import annotations


def test_root_public_api() -> None:
    import src

    for name in [
        "InputFile",
        "OutputArtifact",
        "BatchResult",
        "ProcessOptions",
        "process_files",
        "PRESETS",
        "load_domain",
        "setup_logging",
        "get_logger",
        "get_preset",
        "DOMAIN_JSON_PATH",
    ]:
        assert hasattr(src, name), name


def test_layer_packages() -> None:
    from src import convert, domain, io as io_layer

    assert domain.load_domain().presets
    assert convert.process_files is not None
    assert io_layer.setup_logging is not None
    assert "both_l" in domain.PRESETS
