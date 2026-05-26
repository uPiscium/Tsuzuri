"""Minimal runnable research pipeline."""

from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

from tsuzuri.config import RuntimeConfig
from tsuzuri.fetch.html_fetcher import HtmlFetcher
from tsuzuri.filtering import deduplicate_search_results, filter_search_results
from tsuzuri.schemas import ExtractedDocument, FailedFetch, FilteredUrl, SearchResult
from tsuzuri.search import SearxngClient, build_queries
from tsuzuri.storage import ArtifactStore, WebdavUploader


@dataclass(frozen=True)
class PipelineRunResult:
    """Summary returned by the minimal pipeline."""

    run_id: str
    run_dir: Path
    search_result_count: int
    filtered_url_count: int
    extracted_document_count: int
    failed_fetch_count: int
    warnings: list[str]


class MinimalPipeline:
    """Search, filter, fetch HTML, save artifacts, and optionally upload them."""

    def __init__(
        self,
        config: RuntimeConfig,
        *,
        search_client: SearxngClient | None = None,
        html_fetcher: HtmlFetcher | None = None,
        artifact_store: ArtifactStore | None = None,
        webdav_uploader: WebdavUploader | None = None,
    ) -> None:
        self._config = config
        self._search_client = search_client or SearxngClient(
            base_url=config.searxng_base_url,
            language=config.search_language,
            categories=config.search_categories,
            timeout_sec=config.query_timeout_s,
            retry_count=config.search_retry_count,
        )
        self._html_fetcher = html_fetcher or HtmlFetcher(
            timeout_sec=config.fetch_timeout_s,
            min_chars=config.min_success_chars,
            allowed_languages=set(config.allowed_languages),
            user_agent=config.user_agent,
        )
        self._artifact_store = artifact_store or ArtifactStore(config.output_dir)
        self._webdav_uploader = webdav_uploader or WebdavUploader(
            webdav_url=config.webdav_base_url,
            username=config.nextcloud_username,
            password=config.nextcloud_password,
            timeout_sec=config.upload_timeout_s,
        )

    async def run(self, query: str) -> PipelineRunResult:
        """Run the currently implemented subset of the pipeline."""
        warnings: list[str] = []
        queries = build_queries(
            query, max_generated_queries=self._config.max_generated_queries
        )
        search_results = await self._search_all(queries, warnings)
        deduplicated = deduplicate_search_results(search_results)
        filtered_urls = filter_search_results(
            deduplicated,
            blocked_domains=set(self._config.blocklisted_domains),
            blocked_extensions=set(self._config.blocklisted_extensions),
            max_urls_per_domain=self._config.max_urls_per_domain,
        )
        documents, failures = await self._fetch_html_documents(filtered_urls)

        artifact_paths = [
            self._artifact_store.save_json("queries.json", queries),
            self._artifact_store.save_json("search_results.json", search_results),
            self._artifact_store.save_json("filtered_urls.json", filtered_urls),
            self._artifact_store.save_json("extracted_documents.json", documents),
            self._artifact_store.save_json("failed_fetches.json", failures),
        ]
        warnings.extend(await self._upload_artifacts(artifact_paths))

        summary_path = self._save_summary(
            query=query,
            search_result_count=len(search_results),
            filtered_url_count=len(filtered_urls),
            extracted_document_count=len(documents),
            failed_fetch_count=len(failures),
            warnings=warnings,
        )
        if warnings:
            warnings_path = self._artifact_store.save_json("warnings.json", warnings)
            warnings.extend(await self._upload_artifacts([summary_path, warnings_path]))
            self._save_summary(
                query=query,
                search_result_count=len(search_results),
                filtered_url_count=len(filtered_urls),
                extracted_document_count=len(documents),
                failed_fetch_count=len(failures),
                warnings=warnings,
            )
            self._artifact_store.save_json("warnings.json", warnings)
        else:
            await self._upload_artifacts([summary_path])

        return PipelineRunResult(
            run_id=self._artifact_store.run_id,
            run_dir=self._artifact_store.run_dir,
            search_result_count=len(search_results),
            filtered_url_count=len(filtered_urls),
            extracted_document_count=len(documents),
            failed_fetch_count=len(failures),
            warnings=warnings,
        )

    async def _search_all(
        self, queries: Iterable[str], warnings: list[str]
    ) -> list[SearchResult]:
        results: list[SearchResult] = []
        for query in queries:
            try:
                results.extend(
                    await self._search_client.search(
                        query, max_results=self._config.per_query_results
                    )
                )
            except Exception as error:
                warnings.append(f"Search failed for {query!r}: {error}")
        return results

    async def _fetch_html_documents(
        self, filtered_urls: Iterable[FilteredUrl]
    ) -> tuple[list[ExtractedDocument], list[FailedFetch]]:
        documents: list[ExtractedDocument] = []
        failures: list[FailedFetch] = []
        for item in filtered_urls:
            if item.document_type != "html":
                continue
            result = await self._html_fetcher.fetch(item)
            if isinstance(result, ExtractedDocument):
                documents.append(result)
            else:
                failures.append(result)
        return documents, failures

    async def _upload_artifacts(self, artifact_paths: Iterable[Path]) -> list[str]:
        warnings: list[str] = []
        for path in artifact_paths:
            remote_path = f"{self._artifact_store.run_id}/{path.name}"
            result = await self._webdav_uploader.upload_bytes(
                content=path.read_bytes(),
                remote_path=remote_path,
                content_type="application/json",
            )
            if result.warning is not None:
                warnings.append(result.warning)
        return warnings

    def _save_summary(
        self,
        *,
        query: str,
        search_result_count: int,
        filtered_url_count: int,
        extracted_document_count: int,
        failed_fetch_count: int,
        warnings: list[str],
    ) -> Path:
        return self._artifact_store.save_json(
            "summary.json",
            {
                "run_id": self._artifact_store.run_id,
                "query": query,
                "search_result_count": search_result_count,
                "filtered_url_count": filtered_url_count,
                "extracted_document_count": extracted_document_count,
                "failed_fetch_count": failed_fetch_count,
                "warnings": warnings,
            },
        )
