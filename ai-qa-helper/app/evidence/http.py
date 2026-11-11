"""HTTP GET with the SSRF guard on every redirect hop, a streaming size cap and a total deadline.

qa-service calls ``requests.get(..., allow_redirects=True)`` directly; here redirects are followed
by hand so each hop can be checked, and the body is read in chunks so a large file is cut off.
"""

import time
from dataclasses import dataclass, field
from typing import Any, Protocol
from urllib.parse import urljoin

import requests

from app.evidence.url_guard import Resolver, assert_public_url, dns_resolver

USER_AGENT = "CGIAR-QA-AI-Helper/1.0 (evidence reader)"


@dataclass(frozen=True)
class Fetched:
    url: str
    """Final URL after redirects."""
    status: int
    content_type: str
    body: bytes
    headers: dict[str, str] = field(default_factory=dict)


class TooLargeError(Exception):
    pass


class DeadlineExceeded(Exception):
    pass


class HttpClient(Protocol):
    def get(self, url: str, *, accept: str = "*/*", params: dict[str, str] | None = None) -> Fetched: ...


class GuardedHttp:
    def __init__(
        self,
        max_bytes: int = 25 * 1024 * 1024,
        connect_timeout_s: float = 10.0,
        read_timeout_s: float = 20.0,
        total_timeout_s: float = 45.0,
        max_redirects: int = 5,
        resolve: Resolver = dns_resolver,
        session: Any | None = None,
    ):
        self.max_bytes = max_bytes
        self.timeouts = (connect_timeout_s, read_timeout_s)
        self.total_timeout_s = total_timeout_s
        self.max_redirects = max_redirects
        self.resolve = resolve
        self.session = session or requests.Session()

    def get(self, url: str, *, accept: str = "*/*", params: dict[str, str] | None = None) -> Fetched:
        deadline = time.monotonic() + self.total_timeout_s
        current, current_params = url, params
        for _ in range(self.max_redirects + 1):
            assert_public_url(current, self.resolve)
            resp = self.session.get(
                current,
                params=current_params,
                headers={"User-Agent": USER_AGENT, "Accept": accept},
                timeout=self.timeouts,
                allow_redirects=False,
                stream=True,
            )
            try:
                if 300 <= resp.status_code < 400 and resp.headers.get("location"):
                    current = urljoin(resp.url, resp.headers["location"])
                    current_params = None
                    continue
                body = self._read(resp, deadline)
                return Fetched(
                    url=resp.url,
                    status=resp.status_code,
                    content_type=(resp.headers.get("content-type") or "").lower(),
                    body=body,
                    headers={k.lower(): v for k, v in resp.headers.items()},
                )
            finally:
                resp.close()
        raise requests.TooManyRedirects("too_many_redirects")

    def _read(self, resp: Any, deadline: float) -> bytes:
        declared = resp.headers.get("content-length")
        if declared and declared.isdigit() and int(declared) > self.max_bytes:
            raise TooLargeError(self.max_bytes)
        chunks: list[bytes] = []
        total = 0
        for chunk in resp.iter_content(chunk_size=64 * 1024):
            total += len(chunk)
            if total > self.max_bytes:
                raise TooLargeError(self.max_bytes)
            if time.monotonic() > deadline:
                raise DeadlineExceeded()
            chunks.append(chunk)
        return b"".join(chunks)
