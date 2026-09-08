import pytest
from pydantic import ValidationError

from backend.schemas.file_version import LinkVersionCreate


def test_accepts_trims_and_preserves_url_with_default_mode():
    url = "HTTPS://Example.COM:443/a%2Fb?next=%2Ffoo&x=1#section"
    link = LinkVersionCreate(link_url=f"  {url}  ")
    assert link.model_dump() == {"link_url": url, "link_mode": "redirect"}


def test_accepts_explicit_redirect_mode():
    link = LinkVersionCreate(link_url="https://example.com", link_mode="redirect")
    assert link.link_mode == "redirect"


@pytest.mark.parametrize("url", [
    None, 123, [], "", "http://example.com", "https:///path",
    "https://user:pass@example.com", "https://example.com:65536",
    "https://localhost.", "https://sub.localhost", "https://127.0.0.1",
    "https://[::1]", "https://127.1", "https://exa mple.com",
    "https://example..com", "https://%6cocalhost", "https://example.com\\path",
    "https://exam\nple.com", "https://[2606:4700::1111]junk",
])
def test_invalid_url_is_rejected_at_schema_boundary(url):
    with pytest.raises(ValidationError) as error:
        LinkVersionCreate.model_validate({"link_url": url})
    assert error.value.errors()[0]["loc"] == ("link_url",)


def test_url_is_required():
    with pytest.raises(ValidationError) as error:
        LinkVersionCreate.model_validate({})
    assert error.value.errors()[0]["loc"] == ("link_url",)
    assert error.value.errors()[0]["type"] == "missing"


@pytest.mark.parametrize("mode", ["proxy", "", "REDIRECT", None, 123])
def test_unsupported_mode_is_rejected(mode):
    with pytest.raises(ValidationError) as error:
        LinkVersionCreate(link_url="https://example.com", link_mode=mode)
    assert error.value.errors()[0]["loc"] == ("link_mode",)
