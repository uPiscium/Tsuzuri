# Tsuzuri

Local LLM news research pipeline.

Tsuzuri is an MVP Python implementation of a local-LLM-powered news research
pipeline. It searches, fetches, summarizes, renders a cited Markdown report, and
optionally uploads artifacts to Nextcloud WebDAV.

The current implementation contains a minimal runnable local pipeline. It can
search through SearXNG, filter URLs, fetch HTML documents, summarize through
Ollama, save local artifacts, and optionally upload artifacts to WebDAV.

## MVP Status

This project is ready for local, personal, and demo use through the CLI, HTTP
API, Docker Compose, and React web UI. It is not yet hardened for public
multi-user production deployment.

Production gaps to address before public exposure:

- No authentication or authorization on the API/UI.
- Run state is in memory while the API process is alive.
- Run history is not reconstructed from existing `outputs/` artifacts yet.
- Cluster/global reduce summarization is not implemented.
- Discord notification is not implemented.

## Current Status

Implemented:

- Pydantic schemas for pipeline data.
- URL normalization, deduplication, domain filtering, and document-type routing.
- Rule-based query expansion.
- Async SearXNG JSON API client.
- HTML fetch validation and extraction with `httpx` and `trafilatura`.
- PDF fetching with PyMuPDF.
- Local artifact storage under `outputs/{run_id}/`.
- Minimal orchestrator command for search, filtering, HTML fetch, summarization,
  report rendering, and artifact saving.
- Optional WebDAV artifact upload with warn-and-continue failure behavior.
- Citation extraction, validation, and final Markdown source rendering.
- FastAPI HTTP API for external applications.
- React dark themed web UI with progress polling and final report preview.
- Docker and Docker Compose support.
- Unit tests for the implemented modules.

Not implemented yet:

- Authentication / access control.
- Persistent run history across API restarts.
- Discord notification.
- Cluster/global reduce summarization.

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

## HTTP API

Start the API server:

```bash
just api
```

Health check:

```bash
curl http://127.0.0.1:8000/healthz
```

Run the pipeline from an external app:

```bash
curl -X POST http://127.0.0.1:8000/runs \
  -H 'Content-Type: application/json' \
  -d '{"query":"AI regulation latest developments"}'
```

The response includes run counts, warnings, and the local path to
`final_report.md`.

The API starts runs in the background. Poll `GET /runs/{run_id}` for progress,
then fetch `GET /runs/{run_id}/final-report` after completion.

The React web UI is served from the API after building frontend assets:

```bash
just frontend-build
just api
```

Open `http://127.0.0.1:8000/ui/` for the dark themed run dashboard with progress
polling and final report preview.

For frontend-only development:

```bash
just frontend-dev
```

## Docker

Build the local image:

```bash
just docker-build
```

Run the API with Docker Compose:

```bash
just docker-up
```

Stop it:

```bash
just docker-down
```

The compose service exposes the API on `http://127.0.0.1:8000`, mounts
`./outputs` for artifacts, reads `.env` for secrets when present, and mounts
`settings.toml` read-only inside the container.

The Docker image builds the React frontend and serves it from `/ui/` in the same
FastAPI container.

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

1. Add deterministic document quality filtering.
2. Add cluster/global reduce summarization.
3. Add persistent run history from `outputs/{run_id}/summary.json`.
4. Add API/UI authentication before public deployment.
5. Add Discord notification.
