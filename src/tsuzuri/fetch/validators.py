"""Validation helpers for fetched document text."""

WAF_PATTERNS = [
    "cloudflare",
    "attention required",
    "captcha",
    "enable javascript",
    "403 forbidden",
    "access denied",
    "verify you are human",
    "unusual traffic",
]

NAVIGATION_TERMS = {
    "home",
    "about",
    "contact",
    "privacy",
    "terms",
    "login",
    "subscribe",
    "menu",
}


class FetchValidationError(ValueError):
    """Raised when extracted document text fails deterministic validation."""

    def __init__(self, reason: str, detail: str | None = None) -> None:
        super().__init__(reason if detail is None else f"{reason}: {detail}")
        self.reason = reason
        self.detail = detail


def validate_extracted_text(
    text: str | None,
    *,
    min_chars: int,
    allowed_languages: set[str],
    language: str | None = None,
) -> str:
    """Validate extracted text and return normalized text."""
    normalized = "\n".join(
        line.strip() for line in (text or "").splitlines() if line.strip()
    )
    if len(normalized) < min_chars:
        raise FetchValidationError("text_too_short")

    lower_text = normalized.lower()
    for pattern in WAF_PATTERNS:
        if pattern in lower_text:
            raise FetchValidationError("waf_detected", pattern)

    if _appears_navigation_page(normalized):
        raise FetchValidationError("navigation_page")

    if language is not None and allowed_languages and language not in allowed_languages:
        raise FetchValidationError("language_not_allowed", language)

    return normalized


def _appears_navigation_page(text: str) -> bool:
    words = [word.strip(".,:;!?()[]{}\"'").lower() for word in text.split()]
    if len(words) > 80:
        return False
    navigation_matches = sum(1 for word in words if word in NAVIGATION_TERMS)
    return navigation_matches >= 5
