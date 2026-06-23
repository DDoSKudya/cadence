# Changelog

## 1.0.0 — 2026-06-22

First production-ready release (MVP stages 0–10).

### Features

- Weekly Kanban board with configurable columns, drag-and-drop, task detail drawer
- JSON inbox import with idempotency and background processing
- Background jobs UI with retry/cancel and Celery integration
- Telegram reminders and inline actions (optional)
- Archive, week review, and analytics dashboard with CSV/XLSX export jobs
- Session and API key authentication, project settings

### Infrastructure

- Docker dev stack (nginx, Vite, gunicorn, PostgreSQL, RabbitMQ, Celery, Flower)
- Single `docker-compose.yml` with `dev` / `prod` profiles (`make dev` / `make up`)
- Request ID middleware and structured logging
- Celery task observability logs
- OpenAPI snapshot in `docs/openapi.json`
- CI pipeline for backend and frontend
