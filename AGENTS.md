# AGENTS.md

## Commands
- Use `just check-all` for full verification; it runs `lint -> typecheck -> test`.
- Focused checks: `just lint src/tsuzuri`, `just typecheck src`, `just test tests/test_report.py`.
- Direct equivalents are `uv run ruff check src tests`, `uv run mypy src`, and `uv run pytest`.
- `just format` runs Ruff format and `ruff check --fix`; do not rely on it for tests or typecheck.

## Setup And Config
- This repo is a `uv` + Nix Python project. `.envrc` uses `use flake`, runs `uv sync`, and activates `.venv`.
- Keep secrets in `.env`; `.gitignore` already excludes it. Use `.env.example` for the expected secret keys.
- Keep non-secret endpoints and tunables in `settings.toml`; `RuntimeConfig.from_env()` reads `.env` first, then `TSUZURI_SETTINGS_PATH` or `settings.toml`.
- CLI entrypoint is `tsuzuri` from `pyproject.toml`, implemented by `tsuzuri.cli:main`.

## Architecture Notes
- Main flow is `Search -> Fetch -> Map -> Reduce -> Final Markdown -> Upload` in `src/tsuzuri/pipeline.py`.
- `src/tsuzuri/report.py` owns final Markdown assembly and citation replacement; do not upload raw LLM output from the pipeline.
- `SearchResult.score`, `engine`, and `category` are system metadata. Do not put them into LLM prompts.
- LLM prompt construction is centralized in `build_map_prompt()` and `build_reduce_prompt()`; prompts should only use `doc_id`, `title`, `content`, and map summaries.
- Network and LLM behavior should be mocked in tests; existing tests monkeypatch `urlopen`, component methods, and pipeline dependencies.

## Hooks And Verification
- Pre-commit hooks run Ruff check and Ruff format check via `uv run`.
- Pre-push hook runs `just test`; run `just check-all` before larger changes because pre-push does not typecheck.
- No README exists currently even though `pyproject.toml` references `README.md`; do not assume README guidance is available.
