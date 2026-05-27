"""HTTP API entrypoint for external applications."""

from collections.abc import Callable
from pathlib import Path
from typing import Protocol

from fastapi import FastAPI
from pydantic import BaseModel, ConfigDict, Field

from tsuzuri.config import RuntimeConfig
from tsuzuri.pipeline import MinimalPipeline, PipelineRunResult


class PipelineRunner(Protocol):
    async def run(self, query: str) -> PipelineRunResult: ...


PipelineFactory = Callable[[], PipelineRunner]


class RunRequest(BaseModel):
    """Request body for starting a pipeline run."""

    query: str = Field(min_length=1)


class RunResponse(BaseModel):
    """API response for a completed pipeline run."""

    model_config = ConfigDict(frozen=True)

    run_id: str
    run_dir: str
    search_results: int
    filtered_urls: int
    extracted_documents: int
    failed_fetches: int
    map_summaries: int
    final_report: str | None
    warnings: list[str]


def create_app(pipeline_factory: PipelineFactory | None = None) -> FastAPI:
    """Create the FastAPI application."""
    app = FastAPI(title="Tsuzuri API", version="0.1.0")
    app.state.pipeline_factory = pipeline_factory or _default_pipeline_factory

    @app.get("/healthz")
    async def healthz() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/runs", response_model=RunResponse)
    async def run_pipeline(request: RunRequest) -> RunResponse:
        pipeline: PipelineRunner = app.state.pipeline_factory()
        result = await pipeline.run(request.query)
        return _run_response(result)

    return app


def _default_pipeline_factory() -> MinimalPipeline:
    return MinimalPipeline(RuntimeConfig.from_env())


def _run_response(result: PipelineRunResult) -> RunResponse:
    return RunResponse(
        run_id=result.run_id,
        run_dir=str(result.run_dir),
        search_results=result.search_result_count,
        filtered_urls=result.filtered_url_count,
        extracted_documents=result.extracted_document_count,
        failed_fetches=result.failed_fetch_count,
        map_summaries=result.map_summary_count,
        final_report=_optional_path(result.final_report_path),
        warnings=result.warnings,
    )


def _optional_path(path: Path | None) -> str | None:
    if path is None:
        return None
    return str(path)


app = create_app()
