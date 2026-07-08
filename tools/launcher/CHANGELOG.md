# Changelog

Launcher versioning is independent from the Cadence project. Project release tags (`v*`) do not track launcher releases.

## Unreleased

### Tooling

- Launcher verification in main CI (`pytest` on Ubuntu)
- Ruff and `pytest` hooks in pre-commit / pre-push for `tools/launcher/`
- `Launcher Build` workflow: tests before matrix builds, `uv sync --frozen`

### Documentation

- Russian `README.md` and `docs/LAUNCHER_REFERENCE.md`
- Dedicated launcher `CHANGELOG.md`

## 0.9.1a1 — 2026-07-08

First **alpha** release of the cross-platform desktop launcher for the Cadence production-like Docker stack.

### Added

- PySide6 UI for Linux, macOS, and Windows
- Start prod stack: `docker compose --profile prod up -d --build`
- Stop prod profile only: `docker compose --profile prod down`
- Open app in browser (`NGINX_HTTP_PORT`, default `8080`)
- Stack and service status polling (batched `compose ps --format json`)
- Readiness contract: API health, web root, critical services
- Activity panel during Start/Stop (step, progress, elapsed)
- Splash overlay and button lock during operations
- Rollback (`compose down`) on Start failure or readiness timeout
- Cleanup of partial prod stack before a new Start
- Wait for readiness when prod is already starting
- Repository root discovery: `CADENCE_ROOT`, config, parent walk
- Config in OS user config dir (`repo_root`, `language`)
- EN / RU locale with persisted choice
- `DJANGO_SECRET_KEY` resolution: env → `.env` → `.mise.toml` → fallback with log warning
- Prod environment: `cadence.settings.prod`, `DJANGO_DEBUG=false`, `GUNICORN_EXTRA_ARGS=--workers 2`
- Compose log → user-facing step text (`friendly_action`)
- Launcher log in user log dir (`launcher.log`)
- PyInstaller build script and zip artifacts: `CadenceLauncher-{linux,macos,windows}.zip`
- GitHub Actions `Launcher Build` workflow (matrix: Ubuntu, macOS, Windows)
- Unit tests for runtime, i18n, and Start flows (27 tests)

### Documentation

- Launcher reference: `docs/LAUNCHER_REFERENCE.md`
- README in `tools/launcher/`

### Not in scope (alpha)

- Dev mode, Flower, HMR frontend, nginx-dev
- In-app compose log viewer
- Separate `launcher-v*` release tags
- Installer / auto-setup of Docker and runtime without a git checkout
