"""HTTP API entrypoint for external applications."""

from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Protocol
from uuid import uuid4

from fastapi import BackgroundTasks, FastAPI, HTTPException, status
from fastapi.responses import PlainTextResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field

from tsuzuri.config import RuntimeConfig
from tsuzuri.pipeline import (
    MinimalPipeline,
    PipelineProgress,
    PipelineRunResult,
    ProgressCallback,
)
from tsuzuri.storage import ArtifactStore


class PipelineRunner(Protocol):
    async def run(
        self, query: str, progress_callback: ProgressCallback | None = None
    ) -> PipelineRunResult: ...


PipelineFactory = Callable[[str], PipelineRunner]


class RunRequest(BaseModel):
    """Request body for starting a pipeline run."""

    query: str = Field(min_length=1)


class RunState(BaseModel):
    """Current state for one pipeline run."""

    model_config = ConfigDict(frozen=True)

    run_id: str
    status: str
    step: str
    progress: int
    run_dir: str | None = None
    search_results: int = 0
    filtered_urls: int = 0
    extracted_documents: int = 0
    failed_fetches: int = 0
    map_summaries: int = 0
    final_report: str | None = None
    warnings: list[str] = []
    error: str | None = None
    created_at: str
    updated_at: str


def create_app(pipeline_factory: PipelineFactory | None = None) -> FastAPI:
    """Create the FastAPI application."""
    app = FastAPI(title="Tsuzuri API", version="0.1.0")
    app.state.pipeline_factory = pipeline_factory or _default_pipeline_factory
    app.state.runs = {}

    @app.get("/healthz")
    async def healthz() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/runs", response_model=RunState, status_code=status.HTTP_202_ACCEPTED)
    async def create_run(
        request: RunRequest, background_tasks: BackgroundTasks
    ) -> RunState:
        run_id = _new_run_id()
        state = _initial_state(run_id)
        app.state.runs[run_id] = state
        background_tasks.add_task(_run_pipeline_job, app, run_id, request.query)
        return state

    @app.get("/runs/{run_id}", response_model=RunState)
    async def get_run(run_id: str) -> RunState:
        return _get_state(app, run_id)

    @app.get("/runs/{run_id}/final-report", response_class=PlainTextResponse)
    async def get_final_report(run_id: str) -> str:
        state = _get_state(app, run_id)
        if state.status != "completed":
            raise HTTPException(status_code=409, detail="Run has not completed yet")
        if state.final_report is None:
            raise HTTPException(
                status_code=404, detail="Final report was not generated"
            )
        path = Path(state.final_report)
        if not path.exists():
            raise HTTPException(
                status_code=404, detail="Final report file was not found"
            )
        return path.read_text(encoding="utf-8")

    static_dir = Path(__file__).parent / "static"
    if static_dir.exists():
        app.mount("/ui", StaticFiles(directory=static_dir, html=True), name="ui")

        @app.get("/", include_in_schema=False)
        async def root() -> RedirectResponse:
            return RedirectResponse(url="/ui/")

    return app


def _default_pipeline_factory(run_id: str) -> MinimalPipeline:
    config = RuntimeConfig.from_env()
    return MinimalPipeline(
        config, artifact_store=ArtifactStore(config.output_dir, run_id=run_id)
    )


async def _run_pipeline_job(app: FastAPI, run_id: str, query: str) -> None:
    app.state.runs[run_id] = _update_state(
        app.state.runs[run_id], status="running", step="Starting", progress=1
    )

    async def progress_callback(progress: PipelineProgress) -> None:
        app.state.runs[run_id] = _update_state(
            app.state.runs[run_id],
            status="running",
            step=progress.step,
            progress=progress.progress,
            search_results=progress.search_result_count,
            filtered_urls=progress.filtered_url_count,
            extracted_documents=progress.extracted_document_count,
            failed_fetches=progress.failed_fetch_count,
            map_summaries=progress.map_summary_count,
            warnings=progress.warnings or app.state.runs[run_id].warnings,
        )

    try:
        pipeline: PipelineRunner = app.state.pipeline_factory(run_id)
        result = await pipeline.run(query, progress_callback=progress_callback)
    except Exception as error:
        app.state.runs[run_id] = _update_state(
            app.state.runs[run_id],
            status="failed",
            step="Failed",
            progress=100,
            error=str(error),
        )
        return

    app.state.runs[run_id] = _state_from_result(result)


def _state_from_result(result: PipelineRunResult) -> RunState:
    now = _now()
    return RunState(
        run_id=result.run_id,
        status="completed",
        step="Completed",
        progress=100,
        run_dir=str(result.run_dir),
        search_results=result.search_result_count,
        filtered_urls=result.filtered_url_count,
        extracted_documents=result.extracted_document_count,
        failed_fetches=result.failed_fetch_count,
        map_summaries=result.map_summary_count,
        final_report=_optional_path(result.final_report_path),
        warnings=result.warnings,
        created_at=now,
        updated_at=now,
    )


def _initial_state(run_id: str) -> RunState:
    now = _now()
    return RunState(
        run_id=run_id,
        status="queued",
        step="Queued",
        progress=0,
        created_at=now,
        updated_at=now,
    )


def _update_state(state: RunState, **updates: object) -> RunState:
    return state.model_copy(update={**updates, "updated_at": _now()})


def _get_state(app: FastAPI, run_id: str) -> RunState:
    state = app.state.runs.get(run_id)
    if state is None:
        raise HTTPException(status_code=404, detail="Run not found")
    return state


def _optional_path(path: Path | None) -> str | None:
    if path is None:
        return None
    return str(path)


def _new_run_id() -> str:
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    suffix = uuid4().hex[:8]
    return f"{timestamp}-{suffix}"


def _now() -> str:
    return datetime.now(UTC).isoformat()


app = create_app()
