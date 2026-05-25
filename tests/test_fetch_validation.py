import pytest

from tsuzuri.fetch.validators import FetchValidationError, validate_extracted_text


def test_validate_extracted_text_rejects_short_text() -> None:
    with pytest.raises(FetchValidationError) as exc_info:
        validate_extracted_text("short", min_chars=10, allowed_languages={"en"})

    assert exc_info.value.reason == "text_too_short"


def test_validate_extracted_text_rejects_waf_patterns() -> None:
    with pytest.raises(FetchValidationError) as exc_info:
        validate_extracted_text(
            "Cloudflare says verify you are human before continuing.",
            min_chars=10,
            allowed_languages={"en"},
        )

    assert exc_info.value.reason == "waf_detected"


def test_validate_extracted_text_rejects_navigation_page() -> None:
    with pytest.raises(FetchValidationError) as exc_info:
        validate_extracted_text(
            "Home About Contact Privacy Terms Login Subscribe Menu",
            min_chars=10,
            allowed_languages={"en"},
        )

    assert exc_info.value.reason == "navigation_page"


def test_validate_extracted_text_rejects_unallowed_language() -> None:
    with pytest.raises(FetchValidationError) as exc_info:
        validate_extracted_text(
            "This is a long enough article body for validation.",
            min_chars=10,
            allowed_languages={"en"},
            language="fr",
        )

    assert exc_info.value.reason == "language_not_allowed"
