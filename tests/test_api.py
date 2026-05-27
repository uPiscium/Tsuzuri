from pathlib import Path

from fastapi.testclient import TestClient

from tsuzuri.api import create_app
from tsuzuri.pipeline import PipelineRunResult


class FakePipeline:
    def __init__(self) -> None:
        self.queries: list[str] = []

    async def run(self, query: str) -> PipelineRunResult:
        self.queries.append(query)
        return PipelineRunResult(
            run_id="run-1",
            run_dir=Path("outputs/run-1"),
            search_result_count=10,
            filtered_url_count=8,
            extracted_document_count=6,
            failed_fetch_count=2,
            map_summary_count=5,
            final_report_path=Path("outputs/run-1/final_report.md"),
            warnings=["warning"],
        )


def test_healthz_returns_ok() -> None:
    client = TestClient(create_app(lambda: FakePipeline()))

    response = client.get("/healthz")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_runs_endpoint_executes_pipeline() -> None:
    pipeline = FakePipeline()
    client = TestClient(create_app(lambda: pipeline))

    response = client.post("/runs", json={"query": "AI regulation"})

    assert response.status_code == 200
    assert pipeline.queries == ["AI regulation"]
    assert response.json() == {
        "run_id": "run-1",
        "run_dir": "outputs/run-1",
        "search_results": 10,
        "filtered_urls": 8,
        "extracted_documents": 6,
        "failed_fetches": 2,
        "map_summaries": 5,
        "final_report": "outputs/run-1/final_report.md",
        "warnings": ["warning"],
    }


def test_runs_endpoint_rejects_empty_query() -> None:
    client = TestClient(create_app(lambda: FakePipeline()))

    response = client.post("/runs", json={"query": ""})

    assert response.status_code == 422
