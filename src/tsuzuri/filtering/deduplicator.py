"""Search-result deduplication."""

from collections.abc import Iterable

from tsuzuri.schemas import SearchResult


def deduplicate_search_results(results: Iterable[SearchResult]) -> list[SearchResult]:
    """Keep the first result for each normalized URL."""
    seen: set[str] = set()
    deduplicated: list[SearchResult] = []
    for result in results:
        if result.normalized_url in seen:
            continue
        seen.add(result.normalized_url)
        deduplicated.append(result)
    return deduplicated
