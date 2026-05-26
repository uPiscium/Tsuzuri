import json
from pathlib import Path

from tsuzuri.config import RuntimeConfig
from tsuzuri.pipeline import MinimalPipeline
from tsuzuri.schemas import ExtractedDocument, FilteredUrl, SearchResult
from tsuzuri.storage import ArtifactStore
from tsuzuri.storage.nextcloud_webdav import WebdavUploadResult


class FakeSearchClient:
    async def search(self, query: str, *, max_results: int) -> list[SearchResult]:
        return [
            SearchResult.model_validate(
                {
                    "search_id": f"{query}-1",
                    "query": query,
                    "url": "https://example.com/news",
                    "normalized_url": "https://example.com/news",
                    "title": "Example",
                    "rank": 1,
                }
            )
        ]


class FakeHtmlFetcher:
    async def fetch(self, item: FilteredUrl) -> ExtractedDocument:
        return ExtractedDocument.model_validate(
            {
                "doc_id": "Source-1",
                "url": item.url,
                "normalized_url": item.normalized_url,
                "document_type": "html",
                "title": item.title or "Example",
                "content": "This is extracted content from a test article.",
                "estimated_tokens": 8,
                "domain": item.domain,
                "extraction_method": "httpx_trafilatura",
                "content_hash": "hash",
                "fetched_at": "2026-01-01T00:00:00Z",
                "source_query": item.query,
                "search_rank": item.rank,
            }
        )


class FakeWebdavUploader:
    def __init__(self) -> None:
        self.remote_paths: list[str] = []

    async def upload_bytes(
        self, *, content: bytes, remote_path: str, content_type: str | None = None
    ) -> WebdavUploadResult:
        self.remote_paths.append(remote_path)
        return WebdavUploadResult(
            uploaded=False, skipped=False, warning="upload warning"
        )


def test_minimal_pipeline_saves_artifacts_and_returns_warnings(tmp_path: Path) -> None:
    async def run_pipeline() -> None:
        uploader = FakeWebdavUploader()
        pipeline = MinimalPipeline(
            RuntimeConfig(
                searxng_base_url="https://search.example",
                output_dir=str(tmp_path),
                max_generated_queries=1,
                per_query_results=1,
            ),
            search_client=FakeSearchClient(),
            html_fetcher=FakeHtmlFetcher(),
            artifact_store=ArtifactStore(tmp_path, run_id="run-1"),
            webdav_uploader=uploader,
        )

        result = await pipeline.run("AI regulation")

        assert result.run_id == "run-1"
        assert result.search_result_count == 1
        assert result.filtered_url_count == 1
        assert result.extracted_document_count == 1
        assert result.failed_fetch_count == 0
        assert result.warnings == ["upload warning"] * 7
        assert "run-1/summary.json" in uploader.remote_paths
        assert "run-1/warnings.json" in uploader.remote_paths

    import asyncio

    asyncio.run(run_pipeline())

    summary = json.loads((tmp_path / "run-1" / "summary.json").read_text())
    assert summary["query"] == "AI regulation"
    assert summary["warnings"] == ["upload warning"] * 7
    assert (tmp_path / "run-1" / "warnings.json").exists()
