from tsuzuri.filtering.domain_filter import filter_search_results
from tsuzuri.schemas import SearchResult


def _result(search_id: str, url: str, rank: int = 1) -> SearchResult:
    return SearchResult(
        search_id=search_id, query="q", url=url, normalized_url=url, rank=rank
    )


def test_filter_search_results_blocks_domains_and_extensions_but_keeps_pdf() -> None:
    results = [
        _result("1", "https://example.com/a"),
        _result("2", "https://blocked.example.com/a"),
        _result("3", "https://example.com/image.jpg"),
        _result("4", "https://example.com/report.pdf"),
    ]

    filtered = filter_search_results(
        results,
        blocked_domains={"blocked.example.com"},
        blocked_extensions={".jpg", ".pdf"},
        max_urls_per_domain=5,
    )

    assert [item.search_id for item in filtered] == ["1", "4"]
    assert filtered[1].document_type == "pdf"


def test_filter_search_results_limits_urls_per_domain() -> None:
    filtered = filter_search_results(
        [_result("1", "https://example.com/a"), _result("2", "https://example.com/b")],
        blocked_domains=set(),
        blocked_extensions=set(),
        max_urls_per_domain=1,
    )

    assert [item.search_id for item in filtered] == ["1"]
