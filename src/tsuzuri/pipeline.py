"""Minimal runnable research pipeline."""

from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

from tsuzuri.config import RuntimeConfig
from tsuzuri.fetch.html_fetcher import HtmlFetcher
from tsuzuri.filtering import deduplicate_search_results, filter_search_results
from tsuzuri.llm import MapSummarizer, OllamaClient
from tsuzuri.report import render_news_brief
from tsuzuri.schemas import (
    ExtractedDocument,
    FailedFetch,
    FilteredUrl,
    FinalReport,
    MapSummary,
    SearchResult,
)
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
    map_summary_count: int
    final_report_path: Path | None
    warnings: list[str]


class MinimalPipeline:
    """Search, filter, fetch HTML, save artifacts, and optionally upload them."""

    def __init__(
        self,
        config: RuntimeConfig,
        *,
        search_client: SearxngClient | None = None,
        html_fetcher: HtmlFetcher | None = None,
        map_summarizer: MapSummarizer | None = None,
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
        self._map_summarizer = map_summarizer or MapSummarizer(
            OllamaClient(
                base_url=config.ollama_base_url,
                model=config.ollama_model,
                timeout_sec=config.ollama_timeout_s,
                temperature=config.llm_temperature,
                num_ctx=config.llm_num_ctx,
                retry_count=config.llm_retry_count,
            )
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
        filtered_urls = _assign_source_ids(filtered_urls)
        documents, failures = await self._fetch_html_documents(filtered_urls)
        map_summaries = await self._summarize_documents(documents, warnings)
        final_report = render_news_brief(
            query=query, summaries=map_summaries, documents=documents
        )
        warnings.extend(final_report.warnings)

        artifact_paths = [
            self._artifact_store.save_json("queries.json", queries),
            self._artifact_store.save_json("search_results.json", search_results),
            self._artifact_store.save_json("filtered_urls.json", filtered_urls),
            self._artifact_store.save_json("extracted_documents.json", documents),
            self._artifact_store.save_json("failed_fetches.json", failures),
            self._artifact_store.save_json("map_summaries.json", map_summaries),
            self._artifact_store.save_json("final_report.json", final_report),
            self._artifact_store.save_text("final_report.md", final_report.markdown),
        ]
        warnings.extend(await self._upload_artifacts(artifact_paths))

        summary_path = self._save_summary(
            query=query,
            search_result_count=len(search_results),
            filtered_url_count=len(filtered_urls),
            extracted_document_count=len(documents),
            failed_fetch_count=len(failures),
            map_summary_count=len(map_summaries),
            final_report=final_report,
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
                map_summary_count=len(map_summaries),
                final_report=final_report,
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
            map_summary_count=len(map_summaries),
            final_report_path=self._artifact_store.run_dir / "final_report.md",
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

    async def _summarize_documents(
        self, documents: Iterable[ExtractedDocument], warnings: list[str]
    ) -> list[MapSummary]:
        summaries: list[MapSummary] = []
        for document in list(documents)[: self._config.max_map_documents]:
            try:
                summary = await self._map_summarizer.summarize(document)
            except Exception as error:
                warnings.append(
                    f"Map summarization failed for {document.doc_id}: {error}"
                )
                continue
            if summary.doc_id != document.doc_id:
                warnings.append(
                    f"Map summarization returned mismatched doc_id for {document.doc_id}: {summary.doc_id}"
                )
                continue
            summaries.append(summary)
        return summaries

    async def _upload_artifacts(self, artifact_paths: Iterable[Path]) -> list[str]:
        warnings: list[str] = []
        for path in artifact_paths:
            remote_path = f"{self._artifact_store.run_id}/{path.name}"
            result = await self._webdav_uploader.upload_bytes(
                content=path.read_bytes(),
                remote_path=remote_path,
                content_type=_content_type_for_path(path),
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
        map_summary_count: int,
        final_report: FinalReport,
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
                "map_summary_count": map_summary_count,
                "final_report": "final_report.md",
                "final_report_source_count": final_report.source_count,
                "warnings": warnings,
            },
        )


def _content_type_for_path(path: Path) -> str:
    if path.suffix == ".md":
        return "text/markdown"
    return "application/json"


def _assign_source_ids(filtered_urls: list[FilteredUrl]) -> list[FilteredUrl]:
    return [
        item.model_copy(update={"search_id": f"Source-{index}"})
        for index, item in enumerate(filtered_urls, start=1)
    ]
