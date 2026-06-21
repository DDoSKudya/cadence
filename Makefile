COMPOSE = docker compose

.PHONY: dev up down logs migrate createsuperuser test-backend test-frontend verify worker beat

dev:
	$(COMPOSE) --profile dev up --build

up:
	$(COMPOSE) up -d --build

down:
	$(COMPOSE) down

logs:
	$(COMPOSE) logs -f

migrate:
	$(COMPOSE) run --rm backend uv run python manage.py migrate

createsuperuser:
	$(COMPOSE) run --rm backend uv run python manage.py createsuperuser

test-backend:
	cd backend && uv run pytest

test-frontend:
	cd frontend && npm run typecheck && npm run test -- --run

verify:
	cd backend && uv run ruff check . && uv run ruff format --check . && uv run mypy . && uv run pytest
	cd frontend && npm run typecheck && npm run test -- --run && npm run build

worker:
	cd backend && uv run celery -A cadence worker -l info

beat:
	cd backend && uv run celery -A cadence beat -l info
