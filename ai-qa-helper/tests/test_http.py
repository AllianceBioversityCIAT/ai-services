import pytest

from app.evidence.http import GuardedHttp, TooLargeError
from app.evidence.url_guard import BlockedUrlError


class FakeResponse:
    def __init__(self, url, status=200, headers=None, chunks=(b"",)):
        self.url, self.status_code, self.headers, self._chunks = url, status, headers or {}, chunks
        self.closed = False

    def iter_content(self, chunk_size):
        yield from self._chunks

    def close(self):
        self.closed = True


class FakeSession:
    def __init__(self, responses):
        self.responses = responses
        self.calls = []

    def get(self, url, **kwargs):
        self.calls.append((url, kwargs))
        return self.responses[url]


def http(responses, **kw):
    return GuardedHttp(resolve=lambda h: ["93.184.216.34"], session=FakeSession(responses), **kw)


def test_follows_redirects_checking_each_hop_and_never_lets_requests_redirect():
    client = http({
        "https://a.example/x": FakeResponse("https://a.example/x", 302, {"location": "/y"}),
        "https://a.example/y": FakeResponse("https://a.example/y", 200, {"content-type": "Text/HTML"}, (b"<html>", b"ok")),
    })
    r = client.get("https://a.example/x")
    assert (r.url, r.status, r.content_type, r.body) == ("https://a.example/y", 200, "text/html", b"<html>ok")
    assert all(kw["allow_redirects"] is False and kw["stream"] is True for _, kw in client.session.calls)


def test_redirect_to_metadata_endpoint_is_blocked():
    client = http({"https://a.example/x": FakeResponse("https://a.example/x", 302, {"location": "http://169.254.169.254/"})})
    with pytest.raises(BlockedUrlError):
        client.get("https://a.example/x")


def test_size_cap_on_declared_length_and_while_streaming():
    big = http({"https://a.example/f": FakeResponse("https://a.example/f", 200, {"content-length": "999"})}, max_bytes=10)
    with pytest.raises(TooLargeError):
        big.get("https://a.example/f")
    streamed = http({"https://a.example/f": FakeResponse("https://a.example/f", 200, {}, (b"123456", b"789012"))}, max_bytes=10)
    with pytest.raises(TooLargeError):
        streamed.get("https://a.example/f")
