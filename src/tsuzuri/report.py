"""Final report validation and source rendering."""

import re
from collections.abc import Iterable

from tsuzuri.schemas import ExtractedDocument, FinalReport

SOURCE_ID_PATTERN = re.compile(r"\[Source-(\d+)]")


def extract_cited_source_ids(markdown: str) -> list[str]:
    """Return unique source IDs cited in Markdown, preserving first-seen order."""
    cited: list[str] = []
    seen: set[str] = set()
    for match in SOURCE_ID_PATTERN.finditer(markdown):
        source_id = f"Source-{match.group(1)}"
        if source_id in seen:
            continue
        seen.add(source_id)
        cited.append(source_id)
    return cited


def validate_citations(
    markdown: str, documents: Iterable[ExtractedDocument]
) -> list[str]:
    """Return citation IDs that do not exist in extracted documents."""
    known_ids = {document.doc_id for document in documents}
    return [
        source_id
        for source_id in extract_cited_source_ids(markdown)
        if source_id not in known_ids
    ]


def render_final_report(
    title: str, body_markdown: str, documents: Iterable[ExtractedDocument]
) -> FinalReport:
    """Append a Sources section and return final report metadata."""
    document_by_id = {document.doc_id: document for document in documents}
    cited_source_ids = extract_cited_source_ids(body_markdown)
    warnings = [
        f"Unknown citation: {source_id}"
        for source_id in cited_source_ids
        if source_id not in document_by_id
    ]

    source_lines = []
    for source_id in cited_source_ids:
        document = document_by_id.get(source_id)
        if document is None:
            continue
        source_lines.append(f"- [{source_id}] {document.title} - {document.url}")

    sources_section = "\n".join(source_lines)
    markdown = f"# {title}\n\n{body_markdown.strip()}"
    if sources_section:
        markdown = f"{markdown}\n\n## Sources\n\n{sources_section}"

    return FinalReport(
        title=title,
        markdown=markdown,
        cited_source_ids=cited_source_ids,
        source_count=len(source_lines),
        warnings=warnings,
    )
