.DEFAULT_GOAL := help

COMPOSE := docker compose
COMPOSE_DEV := $(COMPOSE) --profile dev
COMPOSE_PROD := $(COMPOSE) --profile prod
COMPOSE_ALL := $(COMPOSE) --profile dev --profile prod

.PHONY: help up dev down test lint lint-install

help:
	@echo "Cadence — available commands:"
	@echo ""
	@echo "  make up           Start production stack (detached)"
	@echo "  make dev          Start development stack (foreground, logs)"
	@echo "  make down         Stop all services"
	@echo "  make test         Run full test suite (lint, typecheck, tests, build)"
	@echo "  make lint         Run pre-commit on all files"
	@echo "  make lint-install Install pre-commit and pre-push hooks"
	@echo "  make help         Show this help"

up:
	DJANGO_SETTINGS_MODULE=cadence.settings.prod DJANGO_DEBUG=false GUNICORN_EXTRA_ARGS="--workers 2" \
		$(COMPOSE_PROD) up -d --build

dev:
	DJANGO_SETTINGS_MODULE=cadence.settings.dev DJANGO_DEBUG=true GUNICORN_EXTRA_ARGS="--reload" \
		$(COMPOSE_DEV) up --build

down:
	$(COMPOSE_ALL) down

test:
	cd backend && uv run ruff check . && uv run ruff format --check . && uv run mypy . && DJANGO_SETTINGS_MODULE=cadence.settings.test uv run python manage.py makemigrations --check --dry-run && uv run pytest
	cd frontend && npm run typecheck && npm run test -- --run && npm run build

lint:
	uv tool run pre-commit run --all-files --show-diff-on-failure

lint-install:
	uv tool run pre-commit install
	uv tool run pre-commit install --hook-type pre-push
