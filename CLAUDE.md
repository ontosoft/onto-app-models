# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this project does

OntoUI is an application generator: given a SHACL/RDF model that describes a UI and its workflow, the backend interprets it and the frontend renders a generated app that lets users collect data — those interactions in turn produce a knowledge graph. So an "application" here is two things: (a) the static RDF model that defines it, and (b) the runtime state machine that walks a user through it.

## Repository layout

The repo is a single application stack. (A legacy `backend/` + `frontend1/` pair was removed — recoverable from git history at any commit before the removal; see `git log --diff-filter=D -- backend frontend1`.)

- `llm-model-generator/` — the backend. Python 3.13+, FastAPI, SQLModel, PostgreSQL, Alembic, `uv`/`pyproject.toml`. Users/auth, AppModel persistence, Ollama integration, and the model-execution engine. API prefix `/api/v1`. Container name `llm-model-generator-api`, port 8000.
- `frontend/` — the frontend. React 19 + TypeScript + Vite + TanStack Router/Query + Shadcn + Tailwind v4. Auto-generated API client in `src/client/` produced from the llm-model-generator OpenAPI schema.

The OWL/RDF interpretation engine lives in `llm-model-generator/app/owlprocessor/`.

## Dual-write invariant for AppModels

In `llm-model-generator/app/models.py`, every `AppModel` row stores the same knowledge graph **twice**: `knowledge_graph_rdf` (Turtle text) and `knowledge_graph_json` (JSON-LD in a `JSONB` column). The RDF is the source of truth that users edit; the JSON-LD exists to enable Postgres JSONB queries. Any code path that writes one must keep the other in sync — do not update one column in isolation.

## The owlprocessor model (how the runtime "app" works)

The `AppEngine` (in `llm-model-generator/app/owlprocessor/app_engine.py`) holds:
- `internal_app_static_model: AppInternalStaticModel` — built once from the RDF graph via `AppStaticModelFactory.rdf_graf_to_uimodel(...)`. Immutable during a run.
- `process_engine_instance: ProcessEngine` — the runtime state machine. Created when `/run_application` is called and the static model is loaded.

Conceptually: RDF/Turtle file → static model (parsed UI + workflow definition) → ProcessEngine (running app state). The routes (`/upload_rdf_file`, `/run_application`, `/stop_application`, `/app_exchange_post`, `/app_exchange_get`, …) live in `app/api/routes/onto_app_router.py` under the `/api/v1/generator` prefix.

The engine is **per-session multi-tenant**: each request carries an `X-Onto-Session` header, resolved to an isolated `AppEngine` via `app/core/session_service.py`. Engines run either in-process or in a separate `engine-worker` container over Redis, selected by the `ENGINE_TRANSPORT` setting (`local`|`redis`) — see `app/core/engine_transport.py`.

## Common commands

### Backend (`llm-model-generator/`)

Uses `uv` (see `uv.lock`). Run from the `llm-model-generator/` directory.

```bash
# Run dev server (port 8000, /api/v1 prefix)
fastapi dev app/main.py

# Pre-start: DB readiness check + alembic migrations + seed superuser
bash scripts/prestart.sh

# Tests with coverage
bash scripts/test.sh         # = coverage run -m pytest tests/ && coverage report && coverage html

# Lint + format check
bash scripts/lint.sh         # = mypy app && ruff check app && ruff format app --check

# Auto-fix and format
bash scripts/format.sh       # = ruff check ... --fix && ruff format ...

# Alembic migrations
alembic revision --autogenerate -m "message"
alembic upgrade head
```

`Settings` reads `../.env` (the top-level `.env`, **not** one inside `llm-model-generator/`).

### Frontend (`frontend/`)

```bash
bun install
bun run dev                  # vite dev server
bun run build                # tsc + vite build
bun run lint                 # biome check --write
bun run test                 # playwright tests
bun run test:ui              # playwright UI mode
bun run generate-client      # regenerate src/client/ from openapi.json
```

### Regenerating the API client (cross-stack)

When you change endpoints/schemas in `llm-model-generator/`, refresh the frontend client:

```bash
bash scripts/generate-client.sh
# Exports openapi.json from app.main:app, moves it into frontend/, runs openapi-ts, then lints.
```

### Full stack via Docker

```bash
docker-compose up            # brings up ollama, db, redis, prestart (migrations), llm-model-generator-api, engine-worker, frontend, adminer
```

The `prestart` service runs `bash scripts/prestart.sh` against the new backend before `llm-model-generator-api` boots; `db` must be healthy first. The `model-downloader` busybox stage downloads the Mistral GGUF into `model_files/` if missing.

## Environment

Top-level `.env` is the single source of truth for the backend and Docker Compose. Required vars include `POSTGRES_*`, `SECRET_KEY`, `FIRST_SUPERUSER`, `FIRST_SUPERUSER_PASSWORD`, `DOMAIN`, `FRONTEND_HOST`, `ENVIRONMENT`, `BACKEND_CORS_ORIGINS`, `STACK_NAME`, `DOCKER_IMAGE_BACKEND`, `DOCKER_IMAGE_FRONTEND`. The `.secrets` / `.secrets.template` files feed `act` for local GitHub Actions runs.

## Deployment

`infrastructure/terraform/` provisions OpenStack VMs (envs `staging`, `production`); `infrastructure/ansible/` configures them. GitHub Actions in `.github/workflows/{staging,production}-deploy.yml` drive both. For local CI runs, the README suggests `act --secret-file .secrets`.
