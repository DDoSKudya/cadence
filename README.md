# Cadence

Personal weekly Kanban for learning and development work: configurable board, JSON/API intake, background jobs, Telegram reminders, archive, analytics, and CSV/XLSX exports.

**Version 1.0.0** — MVP complete (stages 0–10).

## Stack

| Layer | Technology |
|-------|------------|
| API | Django, DRF, PostgreSQL |
| Jobs | Celery, Celery Beat, RabbitMQ |
| Notifications | aiogram (optional Telegram bot) |
| UI | Vue 3, TypeScript, Vite, Tailwind CSS |
| Tooling | uv, npm, pytest, ruff, mypy, Vitest |

## Architecture

```text
Browser ──► nginx ──► Vue SPA (dev: Vite / prod: static)
              │
              └──► Django API ──► PostgreSQL
                        │
                        └──► Celery workers ──► RabbitMQ
```

**Domain apps** (`backend/apps/`): `boards`, `tasks`, `weeks`, `imports`, `jobs`, `notifications`, `archive`, `analytics`. Shared cross-cutting pieces live in `common` (request id, Celery logging).

**Intake paths:** REST API (session or API key), JSON files in `data/task-inbox/pending/` (Celery scan), Telegram callbacks.

**Observability:** structured console logs with `X-Request-ID`, Celery task start/end/failure logs (`cadence.celery`), Flower in dev profile (`:5556`).

## Bootstrap

```bash
cp .env.example .env
cd backend && uv sync --all-groups
cd ../frontend && npm install
```

## Commands

```bash
make help   # list commands
make dev    # development: Vite, gunicorn --reload, Flower
make up     # production: static SPA in nginx, gunicorn workers
make down   # stop all services
make test   # lint, typecheck, tests, frontend build
```

**Development** — open `http://localhost:8080` (nginx → Vite). API docs: `/api/docs/`. RabbitMQ UI: `:15672`. Flower: `:5556`.

**Production** — set `DJANGO_DEBUG=false`, strong `DJANGO_SECRET_KEY`, and `CSRF_TRUSTED_ORIGINS` in `.env`. Static and media files are served by nginx after `collectstatic`.

Django admin tasks (no make targets):

```bash
docker compose exec backend uv run python manage.py migrate
docker compose exec backend uv run python manage.py createsuperuser
```

## API schema

Live schema: `GET /api/schema/`, Swagger UI: `/api/docs/`. Exported snapshot: `docs/openapi.json`.

## CI

GitHub Actions (`.github/workflows/ci.yml`): backend ruff/mypy/pytest, frontend typecheck/Vitest/build on `main` and `develop`.

## License

MIT
