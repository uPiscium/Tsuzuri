"""Rule-based search query expansion."""

DEFAULT_EXPANSIONS = [
    "United States latest news",
    "European Union latest news",
    "recent updates",
    "industry response",
]


def build_queries(query: str, *, max_generated_queries: int) -> list[str]:
    """Build deterministic search queries, always including the original query."""
    clean_query = " ".join(query.split())
    if max_generated_queries <= 1:
        return [clean_query]

    queries = [clean_query]
    for suffix in DEFAULT_EXPANSIONS:
        if len(queries) >= max_generated_queries:
            break
        expanded = _expand_query(clean_query, suffix)
        if expanded not in queries:
            queries.append(expanded)
    return queries


def _expand_query(query: str, suffix: str) -> str:
    if suffix == "recent updates" and "latest" in query.lower():
        return query.lower().replace("latest", "recent", 1)
    return f"{query} {suffix}"
