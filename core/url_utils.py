"""Utility functions for working with URLs."""

from urllib.parse import urlparse


def is_valid_url(url: str) -> bool:
    """Validate if a URL string has a reasonable format."""
    if not url or not isinstance(url, str):
        return False

    try:
        parsed = urlparse(url.strip())
        if not parsed.scheme or not parsed.netloc:
            return False

        if parsed.scheme not in ["http", "https", "ftp", "ftps"]:
            return False

        domain = parsed.netloc.split(":")[0]
        if not domain or domain.startswith(".") or domain.endswith("."):
            return False

        if domain == "localhost":
            return True

        ip_parts = domain.split(".")
        if len(ip_parts) == 4:
            try:
                for part in ip_parts:
                    num = int(part)
                    if not (0 <= num <= 255):
                        break
                else:
                    return True
            except ValueError:
                pass

        if "." in domain and ".." not in domain:
            allowed = set(
                "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789.-"
            )
            if all(c in allowed for c in domain):
                if not domain.startswith("-") and not domain.endswith("-"):
                    return True

        return False

    except Exception:
        return False
