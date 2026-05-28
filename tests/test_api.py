from pathlib import Path

from fastapi.testclient import TestClient

from tsuzuri.api import create_app
from tsuzuri.pipeline import PipelineProgress, PipelineRunResult, ProgressCallback


class FakePipeline:
    def __init__(self, run_id: str, final_report_path: Path | None = None) -> None:
        self.run_id = run_id
        self.final_report_path = final_report_path
        self.queries: list[str] = []

    async def run(
        self, query: str, progress_callback: ProgressCallback | None = None
    ) -> PipelineRunResult:
        self.queries.append(query)
        if progress_callback is not None:
            await progress_callback(PipelineProgress("Searching", 20))
        return PipelineRunResult(
            run_id=self.run_id,
            run_dir=Path("outputs") / self.run_id,
            search_result_count=10,
            filtered_url_count=8,
            extracted_document_count=6,
            failed_fetch_count=2,
            map_summary_count=5,
            final_report_path=self.final_report_path,
            warnings=["warning"],
        )


def test_healthz_returns_ok() -> None:
    client = TestClient(create_app(lambda run_id: FakePipeline(run_id)))

    response = client.get("/healthz")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_runs_endpoint_starts_pipeline_and_status_can_be_polled(tmp_path: Path) -> None:
    final_report_path = tmp_path / "final_report.md"
    final_report_path.write_text("# Report", encoding="utf-8")
    pipelines: list[FakePipeline] = []

    def factory(run_id: str) -> FakePipeline:
        pipeline = FakePipeline(run_id, final_report_path)
        pipelines.append(pipeline)
        return pipeline

    client = TestClient(create_app(factory))

    response = client.post("/runs", json={"query": "AI regulation"})

    assert response.status_code == 202
    run_id = response.json()["run_id"]
    assert response.json()["status"] == "queued"
    assert pipelines[0].queries == ["AI regulation"]

    status_response = client.get(f"/runs/{run_id}")

    assert status_response.status_code == 200
    assert status_response.json() | {"created_at": "", "updated_at": ""} == {
        "run_id": run_id,
        "status": "completed",
        "step": "Completed",
        "progress": 100,
        "run_dir": f"outputs/{run_id}",
        "search_results": 10,
        "filtered_urls": 8,
        "extracted_documents": 6,
        "failed_fetches": 2,
        "map_summaries": 5,
        "final_report": str(final_report_path),
        "warnings": ["warning"],
        "error": None,
        "created_at": "",
        "updated_at": "",
    }

    report_response = client.get(f"/runs/{run_id}/final-report")
    assert report_response.status_code == 200
    assert report_response.text == "# Report"


def test_runs_endpoint_rejects_empty_query() -> None:
    client = TestClient(create_app(lambda run_id: FakePipeline(run_id)))

    response = client.post("/runs", json={"query": ""})

    assert response.status_code == 422


def test_final_report_endpoint_rejects_incomplete_run() -> None:
    client = TestClient(create_app(lambda run_id: FakePipeline(run_id, None)))

    response = client.post("/runs", json={"query": "AI regulation"})
    run_id = response.json()["run_id"]

    report_response = client.get(f"/runs/{run_id}/final-report")

    assert report_response.status_code == 404
