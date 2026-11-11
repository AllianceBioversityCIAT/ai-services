import pytest

from app.evidence.url_guard import BlockedUrlError, assert_public_url


def public(_host):
    return ["93.184.216.34"]


@pytest.mark.parametrize(
    "url",
    [
        "http://localhost/x",
        "http://127.0.0.1/x",
        "http://10.1.2.3/x",
        "http://169.254.169.254/latest/meta-data",
        "http://[::1]/x",
        "http://[::ffff:127.0.0.1]/x",
        "ftp://example.org/file",
        "https://example.org:8443/x",
        "https://user:pass@example.org/x",
        "https://svc.internal/x",
    ],
)
def test_blocks_local_private_and_odd_urls(url):
    with pytest.raises(BlockedUrlError):
        assert_public_url(url, public)


def test_blocks_public_hostname_that_resolves_to_private_address():
    with pytest.raises(BlockedUrlError) as err:
        assert_public_url("https://evil.example/x", lambda h: ["10.0.0.5"])
    assert err.value.reason == "private_address"


def test_allows_public_https_and_http():
    assert assert_public_url("https://cgspace.cgiar.org/handle/10568/1", public)
    assert assert_public_url("http://example.org/page", public)
