"""Domain and extension filtering for search results."""

from collections import defaultdict
from collections.abc import Iterable

from tsuzuri.filtering.url_normalizer import classify_document_type, get_domain
from tsuzuri.schemas import FilteredUrl, SearchResult


def filter_search_results(
    results: Iterable[SearchResult],
    *,
    blocked_domains: set[str],
    blocked_extensions: set[str],
    max_urls_per_domain: int,
) -> list[FilteredUrl]:
    """Apply deterministic URL filters and per-domain limits."""
    domain_counts: dict[str, int] = defaultdict(int)
    filtered: list[FilteredUrl] = []

    for result in results:
        normalized_url = result.normalized_url
        domain = get_domain(normalized_url)
        if not domain or _is_blocked_domain(domain, blocked_domains):
            continue
        if _has_blocked_extension(normalized_url, blocked_extensions):
            continue
        if domain_counts[domain] >= max_urls_per_domain:
            continue

        domain_counts[domain] += 1
        filtered.append(
            FilteredUrl(
                search_id=result.search_id,
                query=result.query,
                url=result.url,
                normalized_url=normalized_url,
                title=result.title,
                snippet=result.snippet,
                domain=domain,
                rank=result.rank,
                document_type=classify_document_type(normalized_url),
            )
        )

    return filtered


def _is_blocked_domain(domain: str, blocked_domains: set[str]) -> bool:
    return any(
        domain == blocked or domain.endswith(f".{blocked}")
        for blocked in blocked_domains
    )


def _has_blocked_extension(url: str, blocked_extensions: set[str]) -> bool:
    lower_url = url.lower().split("?", maxsplit=1)[0]
    return any(
        lower_url.endswith(extension.lower())
        for extension in blocked_extensions
        if extension.lower() != ".pdf"
    )
