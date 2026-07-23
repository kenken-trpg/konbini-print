"""公開 URL からのファイル取得（SSRF 強化版）.

対策:
- http/https のみ
- プライベート IP / メタデータホスト拒否
- DNS 解決後に IP をピン留めして接続（DNS rebinding 緩和）
- リダイレクトは手動追従し、各ホップで再検証
- サイズ・タイムアウト・URL 件数上限
- KONBINI_ALLOW_URL_FETCH=0 で無効化可能
"""

from __future__ import annotations

import http.client
import ipaddress
import socket
import ssl
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urljoin, urlparse, urlunparse

from .content_sniff import is_supported_payload, validate_and_normalize_name
from .limits import ALLOW_URL_FETCH, MAX_DOWNLOAD_BYTES, MAX_URLS_PER_REQUEST

FETCH_TIMEOUT_SEC = 20.0
MAX_REDIRECTS = 5

_BLOCKED_HOSTS = {
    "localhost",
    "metadata.google.internal",
    "metadata.google.com",
    "metadata",
}


@dataclass
class FetchedFile:
    name: str
    data: bytes
    content_type: str
    url: str


class UrlFetchError(RuntimeError):
    pass


def redact_url_for_log(url: str) -> str:
    """ログ用にクエリを除去する."""
    parsed = urlparse(url)
    return urlunparse((parsed.scheme, parsed.netloc, parsed.path, "", "", ""))


def _filename_from_url(url: str, content_type: str) -> str:
    path = urlparse(url).path
    name = Path(path).name or "download"
    if "." not in name:
        ct = content_type.lower()
        if "png" in ct:
            name += ".png"
        elif "webp" in ct:
            name += ".webp"
        elif "pdf" in ct:
            name += ".pdf"
        elif "jpeg" in ct or "jpg" in ct:
            name += ".jpg"
        elif "heic" in ct or "heif" in ct:
            name += ".heic"
        else:
            name += ".bin"
    return name


def _is_private_ip(ip: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    """非グローバル／プライベート相当を拒否する.

    CGNAT (100.64.0.0/10) は Python の ``is_private`` が False のため、
    ``not is_global`` も見る（メタデータ link-local 等は従来どおり）。
    """
    return bool(
        not ip.is_global
        or ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_multicast
        or ip.is_reserved
        or ip.is_unspecified
    )


def _resolve_public_ips(hostname: str) -> list[str]:
    try:
        infos = socket.getaddrinfo(hostname, None, type=socket.SOCK_STREAM)
    except socket.gaierror as exc:
        raise UrlFetchError(f"ホストを解決できません: {hostname}") from exc

    public: list[str] = []
    seen: set[str] = set()
    for info in infos:
        ip = ipaddress.ip_address(info[4][0])
        if _is_private_ip(ip):
            raise UrlFetchError("プライベート／ローカルアドレスは取得できません。")
        text = str(ip)
        if text not in seen:
            seen.add(text)
            public.append(text)
    if not public:
        raise UrlFetchError(f"公開 IP を解決できません: {hostname}")
    return public


def _validate_url_parts(url: str) -> tuple[str, str, int, str, str]:
    """scheme, hostname, port, path+query, full normalized url を返す."""
    parsed = urlparse(url.strip())
    if parsed.scheme not in {"http", "https"}:
        raise UrlFetchError("http / https の URL のみ対応しています。")
    if not parsed.hostname:
        raise UrlFetchError("ホスト名がありません。")
    host = parsed.hostname.lower()
    if host in _BLOCKED_HOSTS or host.endswith(".local") or host.endswith(".internal"):
        raise UrlFetchError("このホストからは取得できません。")

    # リテラル IP
    try:
        ip = ipaddress.ip_address(host)
        if _is_private_ip(ip):
            raise UrlFetchError("プライベート／ローカルアドレスは取得できません。")
    except ValueError:
        pass

    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    path = parsed.path or "/"
    if parsed.query:
        path = f"{path}?{parsed.query}"
    normalized = urlunparse(
        (parsed.scheme, parsed.netloc.lower(), parsed.path or "/", "", parsed.query, "")
    )
    return parsed.scheme, host, port, path, normalized


def _pick_pinned_ip(hostname: str) -> str:
    # リテラル IP ならそのまま
    try:
        ip = ipaddress.ip_address(hostname)
        if _is_private_ip(ip):
            raise UrlFetchError("プライベート／ローカルアドレスは取得できません。")
        return str(ip)
    except ValueError:
        return _resolve_public_ips(hostname)[0]


def _http_get_pinned(
    scheme: str,
    hostname: str,
    port: int,
    path: str,
    pinned_ip: str,
) -> tuple[int, dict[str, str], bytes]:
    """IP に接続し、TLS は元ホスト名で検証する."""
    timeout = FETCH_TIMEOUT_SEC
    headers = {
        "Host": hostname if port in {80, 443} else f"{hostname}:{port}",
        "User-Agent": "konbini-print/0.1 (public-url-fetch)",
        "Accept": "image/*,application/pdf,*/*",
        "Connection": "close",
    }

    try:
        sock = socket.create_connection((pinned_ip, port), timeout=timeout)
    except OSError as exc:
        raise UrlFetchError(f"接続に失敗しました: {exc}") from exc

    try:
        if scheme == "https":
            context = ssl.create_default_context()
            try:
                sock = context.wrap_socket(sock, server_hostname=hostname)
            except ssl.SSLError as exc:
                try:
                    sock.close()
                except OSError:
                    pass
                raise UrlFetchError(f"TLS 検証に失敗しました: {exc}") from exc

        # 既に接続済みソケットを使う（DNS を再度踏まない）
        conn = http.client.HTTPConnection(pinned_ip, port=port, timeout=timeout)
        conn.sock = sock

        try:
            conn.request("GET", path, headers=headers)
            resp = conn.getresponse()
            resp_headers = {k.lower(): v for k, v in resp.getheaders()}
            cl = resp_headers.get("content-length")
            if cl and cl.isdigit() and int(cl) > MAX_DOWNLOAD_BYTES:
                raise UrlFetchError(
                    f"ファイルが大きすぎます（上限 {MAX_DOWNLOAD_BYTES // 1024 // 1024}MB）。"
                )

            chunks: list[bytes] = []
            total = 0
            while True:
                chunk = resp.read(64 * 1024)
                if not chunk:
                    break
                total += len(chunk)
                if total > MAX_DOWNLOAD_BYTES:
                    raise UrlFetchError(
                        f"ファイルが大きすぎます（上限 {MAX_DOWNLOAD_BYTES // 1024 // 1024}MB）。"
                    )
                chunks.append(chunk)
            return resp.status, resp_headers, b"".join(chunks)
        finally:
            conn.close()
    except UrlFetchError:
        raise
    except OSError as exc:
        raise UrlFetchError(f"取得に失敗しました: {exc}") from exc


def _looks_like_supported_payload(data: bytes, content_type: str, filename: str) -> bool:
    # 拡張子や Content-Type だけでは通さず、マジックバイト必須
    return is_supported_payload(data)


def fetch_public_url(url: str) -> FetchedFile:
    """公開 URL から画像 / PDF を取得する（SSRF 強化）."""
    if not ALLOW_URL_FETCH:
        raise UrlFetchError(
            "URL 取得は無効化されています（KONBINI_ALLOW_URL_FETCH=0）。"
        )

    current = url.strip()
    for _ in range(MAX_REDIRECTS + 1):
        scheme, host, port, path, normalized = _validate_url_parts(current)
        pinned_ip = _pick_pinned_ip(host)
        # ピン留め直前に再解決し、選んだ IP がまだ公開か確認
        try:
            ip_obj = ipaddress.ip_address(pinned_ip)
            if _is_private_ip(ip_obj):
                raise UrlFetchError("プライベート／ローカルアドレスは取得できません。")
        except ValueError as exc:
            raise UrlFetchError("不正な IP です。") from exc

        status, headers, data = _http_get_pinned(scheme, host, port, path, pinned_ip)

        if status in {301, 302, 303, 307, 308}:
            location = headers.get("Location") or headers.get("location")
            if not location:
                raise UrlFetchError(f"リダイレクト先がありません（HTTP {status}）。")
            current = urljoin(normalized, location)
            continue

        if status >= 400:
            raise UrlFetchError(f"取得に失敗しました（HTTP {status}）。")

        content_type = headers.get("content-type", "").split(";")[0].strip()
        # http.client はヘッダを小文字化しない場合がある
        if not content_type:
            content_type = headers.get("Content-Type", "").split(";")[0].strip()

        name = _filename_from_url(normalized, content_type)
        if not _looks_like_supported_payload(data, content_type, name):
            raise UrlFetchError(
                f"対応形式ではありません（Content-Type: {content_type or '不明'}）。"
            )
        try:
            name, _kind = validate_and_normalize_name(name, data)
        except Exception as exc:  # noqa: BLE001
            raise UrlFetchError(str(exc)) from exc

        return FetchedFile(
            name=name, data=data, content_type=content_type, url=normalized
        )

    raise UrlFetchError(f"リダイレクトが多すぎます（上限 {MAX_REDIRECTS}）。")


def parse_url_list(text: str) -> list[str]:
    """改行・カンマ区切りの URL 一覧を正規化する（件数上限あり）."""
    raw = text.replace(",", "\n")
    urls: list[str] = []
    for line in raw.splitlines():
        u = line.strip()
        if u and not u.startswith("#"):
            urls.append(u)
    seen: set[str] = set()
    out: list[str] = []
    for u in urls:
        if u not in seen:
            seen.add(u)
            out.append(u)
    if len(out) > MAX_URLS_PER_REQUEST:
        raise UrlFetchError(
            f"URL 数が上限を超えています（最大 {MAX_URLS_PER_REQUEST} 件）。"
        )
    return out
