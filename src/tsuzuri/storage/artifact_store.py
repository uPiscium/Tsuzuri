"""Local artifact storage."""

from datetime import UTC, datetime
import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel


class ArtifactStore:
    """Save pipeline artifacts under one run directory."""

    def __init__(self, output_dir: str | Path, *, run_id: str | None = None) -> None:
        self.run_id = run_id or _new_run_id()
        self.run_dir = Path(output_dir) / self.run_id
        self.run_dir.mkdir(parents=True, exist_ok=True)

    def save_json(self, filename: str, value: Any) -> Path:
        """Save JSON-serializable data and return the written path."""
        path = self.run_dir / filename
        path.write_text(
            json.dumps(_jsonable(value), ensure_ascii=False, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        return path

    def save_text(self, filename: str, text: str) -> Path:
        """Save text data and return the written path."""
        path = self.run_dir / filename
        path.write_text(text, encoding="utf-8")
        return path


def _new_run_id() -> str:
    return datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")


def _jsonable(value: Any) -> Any:
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json")
    if isinstance(value, list):
        return [_jsonable(item) for item in value]
    if isinstance(value, tuple):
        return [_jsonable(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    return value
