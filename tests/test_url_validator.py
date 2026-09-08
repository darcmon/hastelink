import pytest

from backend.services.url_validator import validate_link_url


@pytest.mark.parametrize("url", [
    "https://example.com",
    "HTTPS://Example.COM:443/a%2Fb?next=%2Ffoo&x=1#section",
    "https://example.com:0/path?#",
    "https://8.8.8.8:8443/path",
    "https://[2606:4700:4700::1111]/path",
    "https://internal.example/path",  # Hostnames are not resolved.
    "https://example.com./path", "https://xn--bcher-kva.example/path",
    "https://my-host.example/path", "https://8.8.8.8./path",
])
def test_accepts_and_preserves_url(url):
    assert validate_link_url(f"  {url}  ") == url


@pytest.mark.parametrize("url", [
    "", "   ", "http://example.com", "//example.com", "https:///path",
    "https://", "https://user@example.com", "https://:pass@example.com",
    "https://user:pass@example.com", "https://@example.com",
    "https://example.com:abc", "https://example.com:-1",
    "https://example.com:65536", "https://example.com:",
    "https://[::1", "https://[not-an-ip]/",
    "https://localhost", "https://LOCALHOST.", "https://a.b.localhost./",
    "https://127.0.0.1", "https://10.0.0.1", "https://172.16.0.1",
    "https://192.168.0.1", "https://169.254.169.254", "https://0.0.0.0",
    "https://100.64.0.1", "https://192.0.2.1", "https://224.0.0.1",
    "https://255.255.255.255", "https://[::1]", "https://[::]",
    "https://[fc00::1]", "https://[fe80::1]", "https://[ff02::1]",
    "https://[2001:db8::1]", "https://[::ffff:127.0.0.1]",
    "https://example.com\\path", "https://example.com/path?x=\\foo",
    "https://exa mple.com", "https://foo_bar.example", "https://.example.com",
    "https://example..com", "https://example.com..", "https://-foo.example",
    "https://foo-.example", "https://%6cocalhost", "https://bücher.example",
    "https://127.0.0.1.", "https://127.1", "https://2130706433",
    "https://0177.0.0.1", "https://0x7f000001", "https://999.999.999.999",
    "https://[2606:4700:4700::1111]junk", "https://[2606:4700::1111%25eth0]",
    f"https://{'a' * 64}.example", f"https://{'.'.join(['a' * 63] * 4)}",
])
def test_rejects_invalid_url(url):
    with pytest.raises(ValueError):
        validate_link_url(url)


@pytest.mark.parametrize("codepoint", [*range(32), *range(127, 160)])
def test_rejects_controls_before_parsing(codepoint):
    with pytest.raises(ValueError, match="control characters"):
        validate_link_url(f"https://exam{chr(codepoint)}ple.com/path")
