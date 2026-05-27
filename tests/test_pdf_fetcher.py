import asyncio

import fitz  # type: ignore[import-untyped]
import httpx

from tsuzuri.fetch.pdf_fetcher import PdfFetcher
from tsuzuri.schemas import ExtractedDocument, FailedFetch, FilteredUrl


def _item() -> FilteredUrl:
    return FilteredUrl.model_validate(
        {
            "search_id": "search-1",
            "query": "AI regulation",
            "url": "https://example.com/report.pdf",
            "normalized_url": "https://example.com/report.pdf",
            "title": "Example PDF",
            "domain": "example.com",
            "rank": 3,
            "document_type": "pdf",
        }
    )


def _pdf_bytes(*, pages: int = 1, text: str = "Useful PDF text") -> bytes:
    document = fitz.open()
    for _ in range(pages):
        page = document.new_page()
        page.insert_text((72, 72), text)
    data = document.write()
    document.close()
    return data


def test_pdf_fetcher_returns_extracted_document() -> None:
    pdf = _pdf_bytes(text="This PDF contains useful extracted article text.")

    async def run() -> None:
        transport = httpx.MockTransport(
            lambda request: httpx.Response(200, content=pdf, request=request)
        )
        async with httpx.AsyncClient(transport=transport) as client:
            fetcher = PdfFetcher(
                timeout_sec=10,
                max_file_mb=1,
                max_pages=5,
                min_chars=20,
                user_agent="Tsuzuri/0.1",
                client=client,
            )
            result = await fetcher.fetch(_item())

        assert isinstance(result, ExtractedDocument)
        assert result.doc_id == "Source-3"
        assert result.document_type == "pdf"
        assert result.extraction_method == "pymupdf_pdf"
        assert "useful extracted article text" in result.content

    asyncio.run(run())


def test_pdf_fetcher_uses_assigned_source_id() -> None:
    pdf = _pdf_bytes(text="This PDF contains useful extracted article text.")
    assigned_item = _item().model_copy(update={"search_id": "Source-42"})

    async def run() -> None:
        transport = httpx.MockTransport(
            lambda request: httpx.Response(200, content=pdf, request=request)
        )
        async with httpx.AsyncClient(transport=transport) as client:
            fetcher = PdfFetcher(
                timeout_sec=10,
                max_file_mb=1,
                max_pages=5,
                min_chars=20,
                user_agent="Tsuzuri/0.1",
                client=client,
            )
            result = await fetcher.fetch(assigned_item)

        assert isinstance(result, ExtractedDocument)
        assert result.doc_id == "Source-42"

    asyncio.run(run())


def test_pdf_fetcher_returns_download_failure_for_http_error() -> None:
    async def run() -> None:
        transport = httpx.MockTransport(
            lambda request: httpx.Response(500, request=request)
        )
        async with httpx.AsyncClient(transport=transport) as client:
            fetcher = PdfFetcher(
                timeout_sec=10,
                max_file_mb=1,
                max_pages=5,
                min_chars=20,
                user_agent="Tsuzuri/0.1",
                client=client,
            )
            result = await fetcher.fetch(_item())

        assert isinstance(result, FailedFetch)
        assert result.reason == "pdf_download_failed"

    asyncio.run(run())


def test_pdf_fetcher_rejects_large_pdf_before_parsing() -> None:
    async def run() -> None:
        transport = httpx.MockTransport(
            lambda request: httpx.Response(200, content=b"x" * 2048, request=request)
        )
        async with httpx.AsyncClient(transport=transport) as client:
            fetcher = PdfFetcher(
                timeout_sec=10,
                max_file_mb=0,
                max_pages=5,
                min_chars=20,
                user_agent="Tsuzuri/0.1",
                client=client,
            )
            result = await fetcher.fetch(_item())

        assert isinstance(result, FailedFetch)
        assert result.reason == "pdf_too_large"

    asyncio.run(run())


def test_pdf_fetcher_rejects_too_many_pages() -> None:
    pdf = _pdf_bytes(pages=2, text="page text")

    async def run() -> None:
        transport = httpx.MockTransport(
            lambda request: httpx.Response(200, content=pdf, request=request)
        )
        async with httpx.AsyncClient(transport=transport) as client:
            fetcher = PdfFetcher(
                timeout_sec=10,
                max_file_mb=1,
                max_pages=1,
                min_chars=1,
                user_agent="Tsuzuri/0.1",
                client=client,
            )
            result = await fetcher.fetch(_item())

        assert isinstance(result, FailedFetch)
        assert result.reason == "pdf_too_many_pages"

    asyncio.run(run())


def test_pdf_fetcher_rejects_too_short_text() -> None:
    pdf = _pdf_bytes(text="tiny")

    async def run() -> None:
        transport = httpx.MockTransport(
            lambda request: httpx.Response(200, content=pdf, request=request)
        )
        async with httpx.AsyncClient(transport=transport) as client:
            fetcher = PdfFetcher(
                timeout_sec=10,
                max_file_mb=1,
                max_pages=5,
                min_chars=20,
                user_agent="Tsuzuri/0.1",
                client=client,
            )
            result = await fetcher.fetch(_item())

        assert isinstance(result, FailedFetch)
        assert result.reason == "pdf_text_too_short"

    asyncio.run(run())


def test_pdf_fetcher_rejects_parse_error() -> None:
    async def run() -> None:
        transport = httpx.MockTransport(
            lambda request: httpx.Response(200, content=b"not a pdf", request=request)
        )
        async with httpx.AsyncClient(transport=transport) as client:
            fetcher = PdfFetcher(
                timeout_sec=10,
                max_file_mb=1,
                max_pages=5,
                min_chars=20,
                user_agent="Tsuzuri/0.1",
                client=client,
            )
            result = await fetcher.fetch(_item())

        assert isinstance(result, FailedFetch)
        assert result.reason == "pdf_parse_error"

    asyncio.run(run())
