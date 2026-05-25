"""Async SearXNG JSON API client."""

import asyncio
from collections.abc import Mapping
from typing import Any

import httpx

from tsuzuri.filtering.url_normalizer import normalize_url
from tsuzuri.schemas import SearchResult

JsonObject = Mapping[str, Any]


class SearxngClient:
    """Small async client for SearXNG search results."""

    def __init__(
        self,
        *,
        base_url: str,
        language: str,
        categories: list[str],
        timeout_sec: float,
        retry_count: int,
        client: httpx.AsyncClient | None = None,
        retry_delay_sec: float = 1.0,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._language = language
        self._categories = categories
        self._timeout = httpx.Timeout(timeout_sec)
        self._retry_count = retry_count
        self._client = client
        self._retry_delay_sec = retry_delay_sec

    async def search(self, query: str, *, max_results: int) -> list[SearchResult]:
        """Search SearXNG and return normalized raw search results."""
        if self._client is not None:
            payload = await self._get_json_with_retry(self._client, query)
        else:
            async with httpx.AsyncClient(
                base_url=self._base_url, timeout=self._timeout
            ) as client:
                payload = await self._get_json_with_retry(client, query)
        return self._parse_results(query, payload, max_results=max_results)

    async def _get_json_with_retry(
        self, client: httpx.AsyncClient, query: str
    ) -> JsonObject:
        attempts = self._retry_count + 1
        last_error: httpx.HTTPError | None = None
        for attempt in range(attempts):
            try:
                response = await client.get(
                    "/search",
                    params={
                        "q": query,
                        "format": "json",
                        "language": self._language,
                        "categories": ",".join(self._categories),
                    },
                )
                response.raise_for_status()
                data = response.json()
                if not isinstance(data, Mapping):
                    raise ValueError("SearXNG response must be a JSON object")
                return data
            except httpx.HTTPError as error:
                last_error = error
                if attempt == attempts - 1:
                    raise
                await asyncio.sleep(self._retry_delay_sec)
        raise RuntimeError("SearXNG retry loop exited unexpectedly") from last_error

    def _parse_results(
        self, query: str, payload: JsonObject, *, max_results: int
    ) -> list[SearchResult]:
        raw_results = payload.get("results", [])
        if not isinstance(raw_results, list):
            return []

        results: list[SearchResult] = []
        for index, raw_result in enumerate(raw_results[:max_results], start=1):
            if not isinstance(raw_result, Mapping):
                continue
            url = raw_result.get("url")
            if not isinstance(url, str) or not url:
                continue
            title = _optional_str(raw_result.get("title"))
            snippet = _optional_str(raw_result.get("content")) or _optional_str(
                raw_result.get("snippet")
            )
            engine = _optional_str(raw_result.get("engine"))
            published_hint = _optional_str(raw_result.get("publishedDate"))

            results.append(
                SearchResult.model_validate(
                    {
                        "search_id": f"search-{index}",
                        "query": query,
                        "url": url,
                        "normalized_url": normalize_url(url),
                        "title": title,
                        "snippet": snippet,
                        "engine": engine,
                        "rank": index,
                        "published_hint": published_hint,
                    }
                )
            )
        return results


def _optional_str(value: object) -> str | None:
    if isinstance(value, str) and value:
        return value
    return None
