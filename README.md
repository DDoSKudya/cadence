# Cadence

Cadence is a personal weekly task manager for learning and development work.

The project is built around a configurable Kanban board, JSON/API task intake, background jobs, Telegram reminders, archive, weekly review, analytics, and CSV/XLSX exports.

## Status

Stage 0 foundation is in progress. Scope and architecture live in `.plan/`.

## Stack

- Backend: Django, Django REST Framework, PostgreSQL
- Background jobs: Celery, Celery Beat, RabbitMQ
- Telegram: aiogram
- Frontend: Vue 3, TypeScript, Vite, Tailwind CSS
- Tooling: uv, npm, pytest, ruff, mypy, Vitest

## Bootstrap

```bash
cp .env.example .env
cd backend && uv sync --all-groups
cd ../frontend && npm install
```

## Development

```bash
make dev
make verify
```

## License

MIT
