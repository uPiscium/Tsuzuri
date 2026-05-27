"""Prompt construction for local LLM steps."""

from tsuzuri.schemas import ExtractedDocument


def build_map_prompt(document: ExtractedDocument) -> str:
    """Build a URL-free prompt for per-document summarization."""
    return f"""You are summarizing a source document for an English news brief.

Rules:
- Return valid JSON only. Do not wrap it in Markdown.
- Do not infer facts not present in the source text.
- Normalize Japanese content into English.
- Use the exact doc_id shown below.
- Do not include URLs.
- If the document is irrelevant or search noise, set is_search_noise=true and relevance_score<=2.

Required JSON schema:
{{
  "doc_id": "{document.doc_id}",
  "title": "string",
  "document_type": "html or pdf",
  "language": "en, ja, or null",
  "relevance_score": 1,
  "is_news_like": true,
  "is_search_noise": false,
  "topic_tags": ["string"],
  "entities": ["string"],
  "event_date": null,
  "published_date": null,
  "key_facts": ["string"],
  "claims": ["string"],
  "uncertainties": ["string"],
  "conflicting_points": ["string"],
  "short_summary": "string"
}}

Doc ID: {document.doc_id}
Title: {document.title}
Document Type: {document.document_type}

Extracted Content:
{document.content[:12000]}
"""


def build_repair_prompt(invalid_json: str, error: str) -> str:
    """Build a prompt that asks the model to repair invalid JSON only."""
    return f"""Repair the following invalid JSON response.

Return valid JSON only. Do not include Markdown or commentary.

Validation error:
{error}

Invalid response:
{invalid_json}
"""
