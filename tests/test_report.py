from datetime import UTC, datetime

from tsuzuri.report import (
    extract_cited_source_ids,
    render_final_report,
    validate_citations,
)
from tsuzuri.schemas import ExtractedDocument


def _document(doc_id: str) -> ExtractedDocument:
    return ExtractedDocument(
        doc_id=doc_id,
        url="https://example.com/news",
        normalized_url="https://example.com/news",
        document_type="html",
        title="Example News",
        content="Long enough content",
        estimated_tokens=3,
        domain="example.com",
        extraction_method="httpx_trafilatura",
        content_hash="abc",
        fetched_at=datetime(2026, 1, 1, tzinfo=UTC),
        source_query="query",
        search_rank=1,
    )


def test_extract_cited_source_ids_preserves_order_and_uniqueness() -> None:
    assert extract_cited_source_ids("A [Source-2] B [Source-1] C [Source-2]") == [
        "Source-2",
        "Source-1",
    ]


def test_validate_citations_returns_unknown_source_ids() -> None:
    assert validate_citations(
        "Fact [Source-1]. Missing [Source-9].", [_document("Source-1")]
    ) == ["Source-9"]


def test_render_final_report_appends_sources_section() -> None:
    report = render_final_report("Title", "Fact [Source-1].", [_document("Source-1")])

    assert report.source_count == 1
    assert report.warnings == []
    assert "## Sources" in report.markdown
    assert "- [Source-1] Example News - https://example.com/news" in report.markdown
