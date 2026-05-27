"""Map summarization for extracted documents."""

import json
from typing import Protocol

from pydantic import ValidationError

from tsuzuri.llm.prompts import build_map_prompt, build_repair_prompt
from tsuzuri.schemas import ExtractedDocument, MapSummary


class ChatClient(Protocol):
    async def chat(self, prompt: str) -> str: ...


class MapSummarizer:
    """Create one structured summary per extracted document."""

    def __init__(self, client: ChatClient) -> None:
        self._client = client

    async def summarize(self, document: ExtractedDocument) -> MapSummary:
        """Summarize one document, retrying once with a JSON repair prompt."""
        raw = await self._client.chat(build_map_prompt(document))
        try:
            return _parse_summary(raw)
        except (json.JSONDecodeError, ValidationError) as error:
            repaired = await self._client.chat(build_repair_prompt(raw, str(error)))
            return _parse_summary(repaired)


def _parse_summary(raw: str) -> MapSummary:
    data = json.loads(_strip_code_fence(raw))
    return MapSummary.model_validate(data)


def _strip_code_fence(raw: str) -> str:
    stripped = raw.strip()
    if not stripped.startswith("```"):
        return stripped
    lines = stripped.splitlines()
    if lines and lines[0].startswith("```"):
        lines = lines[1:]
    if lines and lines[-1].strip() == "```":
        lines = lines[:-1]
    return "\n".join(lines).strip()
