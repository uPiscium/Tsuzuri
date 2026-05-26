"""PDF fetcher using httpx download and PyMuPDF text extraction."""

from datetime import UTC, datetime
import hashlib
from typing import Any

import fitz  # type: ignore[import-untyped]
import httpx

from tsuzuri.schemas import ExtractedDocument, FailedFetch, FilteredUrl


class PdfFetcher:
    """Fetch and extract text from PDF documents."""

    def __init__(
        self,
        *,
        timeout_sec: float,
        max_file_mb: int,
        max_pages: int,
        min_chars: int,
        user_agent: str,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self._timeout = httpx.Timeout(timeout_sec)
        self._max_file_bytes = max_file_mb * 1024 * 1024
        self._max_pages = max_pages
        self._min_chars = min_chars
        self._user_agent = user_agent
        self._client = client

    async def fetch(self, item: FilteredUrl) -> ExtractedDocument | FailedFetch:
        """Fetch one PDF URL and return either an extracted document or failure."""
        try:
            content, status_code = await self._download(item)
        except httpx.HTTPError as error:
            return self._failure(item, "pdf_download_failed", str(error))

        if len(content) > self._max_file_bytes:
            return self._failure(item, "pdf_too_large", str(len(content)))

        try:
            text = self._extract_text(content)
        except _PdfFetchError as error:
            return self._failure(item, error.reason, error.detail)

        if len(text) < self._min_chars:
            return self._failure(item, "pdf_text_too_short", str(len(text)))

        return self._document(item, text, status_code)

    async def _download(self, item: FilteredUrl) -> tuple[bytes, int]:
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
        return response.content, response.status_code

    def _extract_text(self, content: bytes) -> str:
        try:
            document: Any = fitz.open(stream=content, filetype="pdf")
        except Exception as error:
            raise _PdfFetchError("pdf_parse_error", str(error)) from error

        try:
            if document.needs_pass:
                raise _PdfFetchError("pdf_encrypted")
            if document.page_count > self._max_pages:
                raise _PdfFetchError("pdf_too_many_pages", str(document.page_count))
            page_texts = [
                document.load_page(index).get_text()
                for index in range(document.page_count)
            ]
            return "\n".join(text.strip() for text in page_texts if text.strip())
        finally:
            document.close()

    def _document(
        self, item: FilteredUrl, content: str, status_code: int
    ) -> ExtractedDocument:
        return ExtractedDocument.model_validate(
            {
                "doc_id": f"Source-{item.rank}",
                "url": item.url,
                "normalized_url": item.normalized_url,
                "document_type": "pdf",
                "title": item.title or item.domain,
                "content": content,
                "estimated_tokens": max(1, len(content.split())),
                "domain": item.domain,
                "extraction_method": "pymupdf_pdf",
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


class _PdfFetchError(Exception):
    def __init__(self, reason: str, detail: str | None = None) -> None:
        super().__init__(reason if detail is None else f"{reason}: {detail}")
        self.reason = reason
        self.detail = detail
