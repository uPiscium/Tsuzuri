"""Document fetching utilities."""

from tsuzuri.fetch.html_fetcher import HtmlFetcher
from tsuzuri.fetch.validators import FetchValidationError, validate_extracted_text

__all__ = ["FetchValidationError", "HtmlFetcher", "validate_extracted_text"]
