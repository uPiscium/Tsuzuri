import json
from pathlib import Path

from tsuzuri.storage.artifact_store import ArtifactStore


def test_artifact_store_saves_json_and_text(tmp_path: Path) -> None:
    store = ArtifactStore(tmp_path, run_id="run-1")

    json_path = store.save_json("data.json", {"b": 2, "a": 1})
    text_path = store.save_text("report.md", "# Report")

    assert store.run_dir == tmp_path / "run-1"
    assert json.loads(json_path.read_text(encoding="utf-8")) == {"a": 1, "b": 2}
    assert text_path.read_text(encoding="utf-8") == "# Report"
