# Changelog

## Unreleased

### Infrastructure

- Replace local `make`-based developer workflow with cross-platform `mise` tasks and align CI/docs around `.mise.toml`

## 1.1.1 — 2026-06-28

Patch release: board task visibility and UX fixes.

### Fixes

- Board shows all open tasks across ISO weeks; starting a new week no longer hides unfinished work from previous weeks
- Board drag-and-drop animation regression restored (Sortable flip + store sync)
- Story points input no longer blocks task creation when `<input type="number">` yields a numeric value

### Chore

- Ignore local `.refact/` and `.cursor/` tooling directories; remove Refact runtime from git tracking

## 1.1.0 — 2026-06-28

Analytics export refresh: styled reports, live preview, and PDF.

### Features

- Analytics export preview API (`GET /api/v1/analytics/exports/preview/`) — tabular layout aligned with XLSX/PDF output
- PDF export format (WeasyPrint + matplotlib charts) alongside CSV and styled XLSX
- Structured export filenames: report type, period, filters, generation timestamp (ASCII stem)
- Export dialog UI: large modal with sheet tabs and in-browser preview before download

### Improvements

- XLSX exports: multi-sheet layout, charts, localized headers and footnotes
- EC test suite reorganized into `test_ec_*` modules; backend coverage gate unchanged (≥85%)
- Request ID in structured log format; Celery task lifecycle logging
- OpenAPI snapshot updated; export endpoints documented with request/response schemas

### Infrastructure

- Production nginx image (`infra/nginx/Dockerfile`) and `prod.conf` for baked SPA
- Backend Docker image: Cairo/Pango libs for PDF generation
- Dependencies: `weasyprint`, `matplotlib`

## 1.0.0 — 2026-06-22

First production-ready release.

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
