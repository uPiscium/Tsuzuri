"""URL normalization and document-type classification."""

from typing import Literal
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

TRACKING_PARAMETERS = {
    "utm_source",
    "utm_medium",
    "utm_campaign",
    "utm_term",
    "utm_content",
    "fbclid",
    "gclid",
}


def normalize_url(url: str) -> str:
    """Normalize scheme/host, drop fragments, and remove tracking parameters."""
    parts = urlsplit(url.strip())
    scheme = (parts.scheme or "https").lower()
    netloc = parts.netloc.lower()
    if netloc.endswith(":80") and scheme == "http":
        netloc = netloc[:-3]
    if netloc.endswith(":443") and scheme == "https":
        netloc = netloc[:-4]

    query_items = [
        (key, value)
        for key, value in parse_qsl(parts.query, keep_blank_values=True)
        if key.lower() not in TRACKING_PARAMETERS
    ]
    query = urlencode(query_items, doseq=True)
    path = parts.path or "/"
    return urlunsplit((scheme, netloc, path, query, ""))


def get_domain(url: str) -> str:
    """Return a lower-cased hostname without credentials or port."""
    return (urlsplit(url).hostname or "").lower()


def classify_document_type(url: str) -> Literal["html", "pdf", "unknown"]:
    """Classify URLs by extension for initial routing."""
    path = urlsplit(url).path.lower()
    if path.endswith(".pdf"):
        return "pdf"
    if "." not in path.rsplit("/", maxsplit=1)[-1]:
        return "html"
    if path.endswith((".html", ".htm", ".php", ".asp", ".aspx")):
        return "html"
    return "unknown"
