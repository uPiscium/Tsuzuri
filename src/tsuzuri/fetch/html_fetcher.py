"""HTML fetcher using httpx and trafilatura extraction."""

from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
import hashlib

import httpx
import trafilatura

from tsuzuri.fetch.validators import FetchValidationError, validate_extracted_text
from tsuzuri.schemas import ExtractedDocument, FailedFetch, FilteredUrl

Extractor = Callable[[str], str | None]
FallbackFetcher = Callable[[FilteredUrl], Awaitable[str | None]]


class HtmlFetcher:
    """Fetch and extract HTML documents."""

    def __init__(
        self,
        *,
        timeout_sec: float,
        min_chars: int,
        allowed_languages: set[str],
        user_agent: str,
        client: httpx.AsyncClient | None = None,
        extractor: Extractor | None = None,
        fallback_fetcher: FallbackFetcher | None = None,
    ) -> None:
        self._timeout = httpx.Timeout(timeout_sec)
        self._min_chars = min_chars
        self._allowed_languages = allowed_languages
        self._user_agent = user_agent
        self._client = client
        self._extractor = extractor or _extract_with_trafilatura
        self._fallback_fetcher = fallback_fetcher

    async def fetch(self, item: FilteredUrl) -> ExtractedDocument | FailedFetch:
        """Fetch one HTML URL and return either an extracted document or failure."""
        try:
            html, status_code = await self._download(item)
            extracted = self._extractor(html)
            content = validate_extracted_text(
                extracted,
                min_chars=self._min_chars,
                allowed_languages=self._allowed_languages,
            )
            return self._document(item, content, "httpx_trafilatura", status_code)
        except FetchValidationError as error:
            if self._fallback_fetcher is None:
                return self._failure(item, error.reason, error.detail)
            return await self._fetch_with_fallback(item, error)
        except httpx.HTTPStatusError as error:
            return self._failure(
                item, "http_status_error", str(error.response.status_code)
            )
        except httpx.HTTPError as error:
            return self._failure(item, "html_download_failed", str(error))

    async def _download(self, item: FilteredUrl) -> tuple[str, int]:
        if self._client is not None:
            response = await self._client.get(
                str(item.url), headers={"User-Agent": self._user_agent}
            )
        else:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.get(
                    str(item.url), headers={"User-Agent": self._user_agent}
                )
        response.raise_for_status()
        return response.text, response.status_code

    async def _fetch_with_fallback(
        self, item: FilteredUrl, original_error: FetchValidationError
    ) -> ExtractedDocument | FailedFetch:
        if self._fallback_fetcher is None:
            return self._failure(item, original_error.reason, original_error.detail)
        try:
            fallback_text = await self._fallback_fetcher(item)
            content = validate_extracted_text(
                fallback_text,
                min_chars=self._min_chars,
                allowed_languages=self._allowed_languages,
            )
            return self._document(item, content, "playwright_trafilatura", None)
        except FetchValidationError as error:
            return self._failure(item, error.reason, error.detail)
        except Exception as error:
            return self._failure(item, "playwright_failed", str(error))

    def _document(
        self,
        item: FilteredUrl,
        content: str,
        extraction_method: str,
        status_code: int | None,
    ) -> ExtractedDocument:
        return ExtractedDocument.model_validate(
            {
                "doc_id": _doc_id_for_item(item),
                "url": item.url,
                "normalized_url": item.normalized_url,
                "document_type": "html",
                "title": item.title or item.domain,
                "content": content,
                "estimated_tokens": max(1, len(content.split())),
                "domain": item.domain,
                "extraction_method": extraction_method,
                "status_code": status_code,
                "content_hash": hashlib.sha256(content.encode("utf-8")).hexdigest(),
                "fetched_at": datetime.now(UTC),
                "source_query": item.query,
                "search_rank": item.rank,
            }
        )

    def _failure(
        self, item: FilteredUrl, reason: str, detail: str | None = None
    ) -> FailedFetch:
        return FailedFetch.model_validate(
            {
                "url": item.url,
                "normalized_url": item.normalized_url,
                "document_type": item.document_type,
                "domain": item.domain,
                "source_query": item.query,
                "search_rank": item.rank,
                "reason": reason,
                "detail": detail,
                "failed_at": datetime.now(UTC),
            }
        )


def _extract_with_trafilatura(html: str) -> str | None:
    return trafilatura.extract(html, include_comments=False, include_tables=False)


def _doc_id_for_item(item: FilteredUrl) -> str:
    if item.search_id.startswith("Source-"):
        return item.search_id
    return f"Source-{item.rank}"
