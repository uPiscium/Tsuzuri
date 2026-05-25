from tsuzuri.filtering.url_normalizer import (
    classify_document_type,
    get_domain,
    normalize_url,
)


def test_normalize_url_removes_tracking_and_fragment() -> None:
    normalized = normalize_url(
        "HTTPS://Example.COM:443/news?a=1&utm_source=x&fbclid=y#section"
    )

    assert normalized == "https://example.com/news?a=1"


def test_get_domain_lowercases_hostname() -> None:
    assert get_domain("https://USER:PASS@Example.COM:8443/path") == "example.com"


def test_classify_pdf_url() -> None:
    assert classify_document_type("https://example.com/report.pdf?download=1") == "pdf"


def test_classify_extensionless_url_as_html() -> None:
    assert classify_document_type("https://example.com/news/latest") == "html"
