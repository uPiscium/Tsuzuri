"""Runtime configuration loading."""

from __future__ import annotations

import os
from pathlib import Path
import tomllib
from typing import Any

from pydantic import BaseModel, ConfigDict


class RuntimeConfig(BaseModel):
    """Flat runtime config used by the current minimal pipeline."""

    model_config = ConfigDict(frozen=True)

    searxng_base_url: str
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.1"
    webdav_base_url: str | None = None
    query_timeout_s: float = 10.0
    fetch_timeout_s: float = 30.0
    ollama_timeout_s: float = 60.0
    upload_timeout_s: float = 15.0
    max_concurrent_fetches: int = 3
    min_success_chars: int = 200
    blocklisted_domains: list[str] = []
    blocklisted_extensions: list[str] = []
    user_agent: str = "Tsuzuri/0.1"
    output_dir: str = "outputs"
    max_generated_queries: int = 5
    per_query_results: int = 10
    max_urls_per_domain: int = 5
    search_language: str = "en"
    search_categories: list[str] = ["news", "general"]
    search_retry_count: int = 2
    allowed_languages: list[str] = ["en", "ja"]
    llm_temperature: float = 0.2
    llm_num_ctx: int = 8192
    llm_retry_count: int = 1
    max_map_documents: int = 20
    min_relevance_score: int = 3
    nextcloud_username: str | None = None
    nextcloud_password: str | None = None
    discord_webhook_url: str | None = None

    @classmethod
    def from_env(cls, *, env_file: str | Path = ".env") -> RuntimeConfig:
        """Load settings.toml plus .env/environment secrets."""
        env_values = _load_env_file(Path(env_file))
        settings_path = Path(
            os.environ.get("TSUZURI_SETTINGS_PATH")
            or env_values.get("TSUZURI_SETTINGS_PATH")
            or "settings.toml"
        )
        settings = _load_toml(settings_path)
        merged = {
            **settings,
            "nextcloud_username": _env_value("NEXTCLOUD_USERNAME", env_values),
            "nextcloud_password": _env_value("NEXTCLOUD_PASSWORD", env_values),
            "discord_webhook_url": _env_value("DISCORD_WEBHOOK_URL", env_values),
        }
        return cls.model_validate(merged)


def _load_toml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    with path.open("rb") as file:
        data = tomllib.load(file)
    return data


def _load_env_file(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    values: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", maxsplit=1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def _env_value(key: str, env_values: dict[str, str]) -> str | None:
    value = os.environ.get(key, env_values.get(key))
    if value is None or value == "":
        return None
    return value
