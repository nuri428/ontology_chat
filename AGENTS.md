# Repository Guidelines

## Project Structure & Module Organization
- Backend (`api/`): FastAPI app in `api/main.py`; routers in `api/routers/`, business logic in `api/services/`, adapters (MCP, DB, search) in `api/adapters/`, pipeline in `api/graph/`, shared config in `api/config.py` and `api/config/`.
- Frontend (`ui/`): Streamlit entrypoint at `ui/main.py`.
- Ops: Docker Compose files, `Dockerfile.*`, `monitoring/`, `nginx/`, and helper `scripts/`.
- Tooling: `Makefile`, `pyproject.toml`, `uv.lock`, `.env` (local only).

## Build, Test, and Development Commands
- Run API: `make api` (uvicorn with reload at `:8000`).
- Run UI: `make ui` (Streamlit at `:8501`).
- Tests: `make test` or `uv run pytest -q`.
- Format: `make fmt` (ruff fix + black).
- Type check: `make typecheck` (pyright).
- Docker (dev): `make docker-dev-up` / `make docker-dev-down` / `make docker-dev-logs`.
- Docker (prod): `make docker-prod-deploy` / `make docker-prod-logs`.

## Coding Style & Naming Conventions
- Python 3.10+; 4‑space indent; PEP 8 enforced by `ruff` and `black`.
- Type hints for all public functions; prefer `pydantic` models for I/O.
- Names: files/modules `snake_case.py`; classes `PascalCase`; functions/vars `snake_case`.
- API routers live in `api/routers/*.py`; services in `api/services/*_service.py`; adapters in `api/adapters/mcp_*.py`.
- Logging via `api/logging.py` and `loguru`; avoid `print`.

## Testing Guidelines
- Framework: `pytest`. Place tests under `tests/` mirroring `api/` (e.g., `tests/routers/test_health.py`).
- Names: `test_*.py`, functions `test_*`.
- Run fast, deterministic tests locally: `uv run pytest -q`.
- Aim for practical coverage of routers, services, and adapters; include one happy‑path and key edge‑cases per endpoint/service method.

## Commit & Pull Request Guidelines
- Commits: concise imperative subject; optionally follow Conventional Commits (e.g., `feat(api): add report endpoint`).
- PRs: clear description (what/why/how), linked issue, steps to test, and screenshots for UI changes. Note config/env changes and update docs where relevant.
- Keep PRs focused and reviewable; include `make fmt` and `make typecheck` before pushing.

## Security & Configuration Tips
- Do not commit secrets. Use environment variables (`.env` for local only). Rotate API keys when needed.
- External deps: Neo4j, OpenSearch; verify endpoints in `.env` and `api/config.py`.
- Validate inputs at boundaries (routers) with `pydantic`.

## Architecture Overview
- Streamlit UI ↔ FastAPI API ↔ Neo4j/OpenSearch. MCP adapters under `api/adapters/` encapsulate external data access. Prefer adding new integrations as adapters and expose via routers/services.
