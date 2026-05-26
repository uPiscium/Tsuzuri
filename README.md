# Tsuzuri

Local LLM news research pipeline.

Tsuzuri is an in-progress Python implementation of a local-LLM-powered news
research pipeline. The target flow is search, fetch, filter, summarize, render a
cited Markdown report, and optionally upload or notify through external services.

The current implementation contains the foundation modules only. It is not yet a
complete runnable research pipeline.

## Current Status

Implemented:

- Pydantic schemas for pipeline data.
- URL normalization, deduplication, domain filtering, and document-type routing.
- Rule-based query expansion.
- Async SearXNG JSON API client.
- HTML fetch validation and extraction with `httpx` and `trafilatura`.
- Citation extraction, validation, and final Markdown source rendering.
- Unit tests for the implemented modules.

Not implemented yet:

- PDF fetcher.
- Orchestrator pipeline.
- Ollama map/reduce summarization.
- Artifact store.
- Nextcloud WebDAV upload.
- Discord notification.

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

Run the current local smoke command:

```bash
just deploy
```

At this stage it starts the placeholder CLI and prints:

```text
tsuzuri: pipeline implementation is in progress
```

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
3. Add local artifact storage.
4. Add a minimal orchestrator command that writes local artifacts.
5. Add Ollama map/reduce summarization.
