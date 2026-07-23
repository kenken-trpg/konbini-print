"""fetch_url / SSRF 単体テスト（ネットワーク不要）."""

import pytest

import ipaddress

from src.fetch_url import (
    UrlFetchError,
    parse_url_list,
    redact_url_for_log,
    _is_private_ip,
    _pick_pinned_ip,
    _resolve_public_ips,
    _validate_url_parts,
)


def test_parse_url_list_dedup_and_comments() -> None:
    text = """
    https://a.example/x.jpg
    # comment
    https://b.example/y.png, https://a.example/x.jpg
    """
    assert parse_url_list(text) == [
        "https://a.example/x.jpg",
        "https://b.example/y.png",
    ]


def test_parse_url_list_rejects_too_many(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("src.fetch_url.MAX_URLS_PER_REQUEST", 2)
    with pytest.raises(UrlFetchError, match="URL 数"):
        parse_url_list("\n".join(f"https://ex.com/{i}.jpg" for i in range(5)))


@pytest.mark.parametrize(
    "url",
    [
        "file:///tmp/x.jpg",
        "ftp://example.com/x.jpg",
        "http://127.0.0.1/x.jpg",
        "http://192.168.0.1/x.jpg",
        "http://10.0.0.1/x.jpg",
        "http://100.64.0.1/x.jpg",  # CGNAT
        "http://localhost/x.jpg",
        "http://[::1]/x.jpg",
        "http://metadata.google.internal/latest",
    ],
)
def test_validate_url_parts_blocks_unsafe(url: str) -> None:
    with pytest.raises(UrlFetchError):
        _validate_url_parts(url)


def test_is_private_ip_blocks_cgnat() -> None:
    assert _is_private_ip(ipaddress.ip_address("100.64.0.1"))
    assert _is_private_ip(ipaddress.ip_address("100.127.255.254"))
    assert not _is_private_ip(ipaddress.ip_address("8.8.8.8"))


def test_pick_pinned_ip_public(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "src.fetch_url._resolve_public_ips",
        lambda _host: ["93.184.216.34"],
    )
    assert _pick_pinned_ip("example.com") == "93.184.216.34"


def test_pick_pinned_ip_rejects_private_literal() -> None:
    with pytest.raises(UrlFetchError):
        _pick_pinned_ip("127.0.0.1")


def test_resolve_blocks_private_dns(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "src.fetch_url.socket.getaddrinfo",
        lambda *_a, **_k: [(None, None, None, None, ("127.0.0.1", 0))],
    )
    with pytest.raises(UrlFetchError, match="プライベート"):
        _resolve_public_ips("evil.example")


def test_redact_url_strips_query() -> None:
    assert (
        redact_url_for_log("https://ex.com/a.jpg?token=secret")
        == "https://ex.com/a.jpg"
    )


def test_allow_url_fetch_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("src.fetch_url.ALLOW_URL_FETCH", False)
    from src.fetch_url import fetch_public_url

    with pytest.raises(UrlFetchError, match="無効"):
        fetch_public_url("https://example.com/a.jpg")
