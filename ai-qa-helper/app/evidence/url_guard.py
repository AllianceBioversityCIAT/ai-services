"""SSRF guard for evidence links (untrusted input typed by submitters).

Allows http/https on default ports to public addresses only. Every redirect hop is re-checked
by ``GuardedHttp``. Known limit: DNS is resolved here and again by the HTTP client (TOCTOU).
The worker Lambda runs outside any VPC, so the remaining exposure is loopback and link-local
(the Lambda runtime API and metadata endpoints), which are blocked here.
"""

import ipaddress
import socket
from collections.abc import Callable
from urllib.parse import urlsplit

Resolver = Callable[[str], list[str]]


class BlockedUrlError(Exception):
    def __init__(self, reason: str):
        super().__init__(f"blocked url: {reason}")
        self.reason = reason


def dns_resolver(hostname: str) -> list[str]:
    return sorted({info[4][0] for info in socket.getaddrinfo(hostname, None)})


def is_blocked_address(address: str) -> bool:
    try:
        ip = ipaddress.ip_address(address.split("%", 1)[0])
    except ValueError:
        return True
    if isinstance(ip, ipaddress.IPv6Address) and ip.ipv4_mapped:
        ip = ip.ipv4_mapped
    return not ip.is_global or ip.is_multicast


def assert_public_url(raw: str, resolve: Resolver = dns_resolver) -> str:
    try:
        parts = urlsplit(raw)
        port = parts.port
    except ValueError as err:
        raise BlockedUrlError("invalid_url") from err
    if parts.scheme not in ("http", "https"):
        raise BlockedUrlError("scheme")
    if parts.username or parts.password:
        raise BlockedUrlError("credentials_in_url")
    if port is not None and port not in (80, 443):
        raise BlockedUrlError("non_default_port")
    host = (parts.hostname or "").rstrip(".").lower()
    if not host:
        raise BlockedUrlError("invalid_url")
    if host == "localhost" or host.endswith((".localhost", ".internal", ".local")):
        raise BlockedUrlError("local_hostname")
    try:
        ipaddress.ip_address(host)
        addresses = [host]
    except ValueError:
        try:
            addresses = resolve(host)
        except OSError as err:
            raise BlockedUrlError("dns") from err
    if not addresses or any(is_blocked_address(a) for a in addresses):
        raise BlockedUrlError("private_address")
    return raw
