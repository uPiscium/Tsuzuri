from tsuzuri.filtering.deduplicator import deduplicate_search_results
from tsuzuri.schemas import SearchResult


def test_deduplicate_search_results_keeps_first_normalized_url() -> None:
    first = SearchResult(
        search_id="1",
        query="q",
        url="https://example.com/a",
        normalized_url="https://example.com/a",
        rank=1,
    )
    second = SearchResult(
        search_id="2",
        query="q",
        url="https://example.com/a?utm_source=x",
        normalized_url="https://example.com/a",
        rank=2,
    )

    assert deduplicate_search_results([first, second]) == [first]
