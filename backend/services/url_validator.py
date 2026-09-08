from ipaddress import ip_address
import re
from urllib.parse import urlsplit


def validate_link_url(value: str) -> str:
    """Validate a URL without I/O and return it with surrounding whitespace trimmed.

    Only literal IP addresses are checked for public reachability; a hostname
    passing validation is not guaranteed to resolve to a public address.
    """
    value = value.strip()
    if any(ord(char) < 32 or 127 <= ord(char) <= 159 for char in value):
        raise ValueError("URL must not contain control characters")
    if "\\" in value:
        raise ValueError("URL must not contain backslashes")

    # urlsplit can reject malformed authorities; accessing port also validates
    # its syntax and range. Let those ValueErrors propagate to the caller.
    parts = urlsplit(value)
    hostname = parts.hostname
    if parts.scheme != "https" or not hostname:
        raise ValueError("URL must use HTTPS and include a hostname")
    if parts.username is not None or parts.password is not None:
        raise ValueError("URL must not contain a username or password")
    _ = parts.port
    if parts.netloc.endswith(":"):
        raise ValueError("URL port must not be empty")
    if parts.netloc.startswith("[") and not re.fullmatch(
        r"\[[^\[\]]+\](?::[0-9]+)?", parts.netloc
    ):
        raise ValueError("URL has an invalid IPv6 authority")
    if "%" in hostname:
        raise ValueError("URL hostname must not contain escapes or IPv6 scope IDs")

    # A trailing DNS root dot does not change whether a host is localhost.
    host = hostname.removesuffix(".").lower()
    if host == "localhost" or host.endswith(".localhost"):
        raise ValueError("URL must not target localhost")

    try:
        address = ip_address(host)
    except ValueError:
        # Accept ASCII DNS labels, including Punycode. Unicode hostnames must
        # be supplied as Punycode so browser normalization cannot change them.
        labels = host.split(".")
        if len(host) > 253 or any(
            not re.fullmatch(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?", label)
            for label in labels
        ):
            raise ValueError("URL has an invalid hostname")
        # Browsers can interpret shortened, integer, octal, or hexadecimal
        # hosts as IPv4 even though ip_address rejects those representations.
        if re.fullmatch(r"[0-9]+|0x[0-9a-f]+", labels[-1]):
            raise ValueError("URL must not use an ambiguous numeric hostname")
    else:
        if not address.is_global or address.is_multicast:
            raise ValueError("URL must not target a non-public IP address")

    return value
