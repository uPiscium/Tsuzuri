# Tsuzuri

Local LLM news research pipeline.

Tsuzuri is an in-progress Python implementation of a local-LLM-powered news
research pipeline. The target flow is search, fetch, filter, summarize, render a
cited Markdown report, and optionally upload or notify through external services.

The current implementation contains a minimal runnable local pipeline. It can
search through SearXNG, filter URLs, fetch HTML documents, save local artifacts,
and optionally upload artifacts to WebDAV. LLM summarization is not implemented
yet.

## Current Status

Implemented:

- Pydantic schemas for pipeline data.
- URL normalization, deduplication, domain filtering, and document-type routing.
- Rule-based query expansion.
- Async SearXNG JSON API client.
- HTML fetch validation and extraction with `httpx` and `trafilatura`.
- Local artifact storage under `outputs/{run_id}/`.
- Minimal orchestrator command for search, filtering, HTML fetch, and artifact
  saving.
- Optional WebDAV artifact upload with warn-and-continue failure behavior.
- Citation extraction, validation, and final Markdown source rendering.
- Unit tests for the implemented modules.

Not implemented yet:

- PDF fetcher.
- Ollama map/reduce summarization.
- Discord notification.
- PDF fetcher.

## Requirements

- Python 3.11 or newer.
- `uv`.
- Optional: Nix with direnv support for the repository flake workflow.

## Setup

Synchronize dependencies:

```bash
just sync
```

Or directly:

```bash
uv sync
```

Copy `.env.example` to `.env` when enabling external services later:

```bash
cp .env.example .env
```

Do not commit real secrets.

## Local Run

Run the default local pipeline:

```bash
just deploy
```

Run with a custom query:

```bash
just deploy "AI regulation latest developments"
```

Or call the CLI directly:

```bash
PYTHONPATH=src uv run python -m tsuzuri.cli run "AI regulation latest developments"
```

Artifacts are saved under `outputs/{run_id}/`. WebDAV upload is attempted when
`webdav_base_url`, `NEXTCLOUD_USERNAME`, and `NEXTCLOUD_PASSWORD` are available.
Upload failures are reported as warnings and do not fail the run.

## Development

Run all checks:

```bash
just check-all
```

Focused commands:

```bash
just lint src/
just typecheck src/
just test tests/
```

Format source and tests:

```bash
just format src/
uv run ruff format tests/
uv run ruff check --fix tests/
```

## Configuration

Non-secret defaults live in `settings.toml`.

Secret values are expected through environment variables, with placeholders in
`.env.example`:

- `NEXTCLOUD_USERNAME`
- `NEXTCLOUD_PASSWORD`
- `DISCORD_WEBHOOK_URL`

## Roadmap

Next implementation slices:

1. Add PDF fetching with PyMuPDF.
2. Add deterministic document quality filtering.
3. Add Ollama map/reduce summarization.
4. Add final report rendering into the orchestrator.
5. Add Discord notification.
