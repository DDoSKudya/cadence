<div align="center">

<div align="center">
  <img src="docs/cadence-icon.png" alt="Cadence" width="96" height="96">
  <h1><b>Cadence</b></h1>
  <p>
    <strong>Персональный недельный Kanban для обучения и pet-проектов</strong><br>
  </p>
  <p>
    <a href="CHANGELOG.md"><img alt="Version" src="https://img.shields.io/badge/version-1.1.1-111827?style=flat-square"></a>
    <a href="https://www.python.org/"><img alt="Python" src="https://img.shields.io/badge/Python-3.12-3776AB?style=flat-square&logo=python&logoColor=white"></a>
    <a href="https://www.djangoproject.com/"><img alt="Django" src="https://img.shields.io/badge/Django-6.0-092E20?style=flat-square&logo=django&logoColor=white"></a>
    <a href="https://vuejs.org/"><img alt="Vue" src="https://img.shields.io/badge/Vue-3.5-4FC08D?style=flat-square&logo=vuedotjs&logoColor=white"></a>
    <a href="LICENSE"><img alt="License" src="https://img.shields.io/badge/license-MIT-16A34A?style=flat-square"></a>
  </p>
</div>

<p>
  <a href="#быстрый-старт">Быстрый старт</a>
  ·
  <a href="#архитектура">Архитектура</a>
  ·
  <a href="#api">API</a>
  ·
  <a href="CHANGELOG.md">Changelog</a>
  ·
  <a href="docs/DEVELOPERS.md">Developers</a>
  ·
  <a href=".github/workflows/ci.yml">CI</a>
</p>

</div>

---

<table>
  <tr>
    <td><strong>Назначение</strong></td>
    <td>Self-hosted Kanban вокруг недельного ритма: доска, импорт, фоновые задания, Telegram, архив и аналитика.</td>
  </tr>
  <tr>
    <td><strong>Демо</strong></td>
    <td><a href="https://kudyasoft-cadence.hf.space/">
    <img alt="Open demo" src="https://img.shields.io/badge/Открыть_демо-Hugging_Face-FFD21E?style=for-the-badge&logo=huggingface&logoColor=black">
  </a></td>
  </tr>
  <tr>
    <td><strong>Формат</strong></td>
    <td>Модульный монолит: Django apps + Vue SPA, один <code>docker-compose.yml</code> с профилями <code>dev</code> / <code>prod</code>.</td>
  </tr>
  <tr>
    <td><strong>Акцент</strong></td>
    <td>Настраиваемый workflow (схемы досок, граф статусов), несколько каналов ввода задач, наблюдаемость фоновых job.</td>
  </tr>
</table>

## Оглавление

<table>
  <tr>
    <td width="33%">
      <strong>Start</strong><br>
      <a href="#быстрый-старт">Быстрый старт</a><br>
      <a href="#запуск">Запуск</a><br>
      <a href="#переменные-окружения">Переменные окружения</a><br>
      <a href="#качество-кода">Качество кода</a>
    </td>
    <td width="33%">
      <strong>System</strong><br>
      <a href="#стек">Стек</a><br>
      <a href="#архитектура">Архитектура</a><br>
      <a href="#api">API</a><br>
      <a href="#возможности">Возможности</a>
    </td>
    <td width="33%">
      <strong>Ops</strong><br>
      <a href="#данные-и-логи">Данные и логи</a><br>
      <a href="#тесты">Тесты</a><br>
      <a href="#деплой">Деплой</a><br>
      <a href="#документация">Документация</a>
    </td>
  </tr>
</table>

---

## Быстрый старт

```bash
cp .env.example .env
mise trust
mise install
mise run dev   # Docker: SPA + API на :8080
mise run test  # ruff + mypy + pytest + vitest + build
```

<table>
  <tr>
    <td><strong>Приложение</strong></td>
    <td><a href="http://localhost:8080">http://localhost:8080</a></td>
  </tr>
  <tr>
    <td><strong>Health</strong></td>
    <td><a href="http://localhost:8080/api/health/">http://localhost:8080/api/health/</a></td>
  </tr>
  <tr>
    <td><strong>Swagger</strong></td>
    <td><a href="http://localhost:8080/api/docs/">http://localhost:8080/api/docs/</a></td>
  </tr>
  <tr>
    <td><strong>RabbitMQ</strong></td>
    <td><a href="http://localhost:15672">http://localhost:15672</a> (<code>cadence</code> / <code>cadence</code>)</td>
  </tr>
  <tr>
    <td><strong>Flower</strong></td>
    <td><a href="http://localhost:5556">http://localhost:5556</a> (только <code>mise run dev</code>)</td>
  </tr>
  <tr>
    <td><strong>Vite</strong></td>
    <td><a href="http://localhost:5173">http://localhost:5173</a> (только <code>mise run dev</code>)</td>
  </tr>
  <tr>
    <td><strong>Admin</strong></td>
    <td><a href="http://localhost:8080/admin/">http://localhost:8080/admin/</a></td>
  </tr>
</table>

Первый вход — создайте суперпользователя:

```bash
docker compose exec backend uv run python manage.py createsuperuser
```

## Запуск

**Нужно:** [mise](https://mise.jdx.dev/) и Docker Compose. `mise` сам подтянет Python 3.12, Node 22 и `uv` из конфигурации проекта.

`mise tasks` покажет основные команды: `dev`, `up`, `down`, `lint`, `test`.

### Docker

```bash
cp .env.example .env
mise run dev    # разработка: foreground, логи в терминале
mise run up     # production-like: baked SPA, gunicorn workers, detached
mise run down   # остановить все профили
```

nginx слушает порт **8080**. Порт можно поменять через `NGINX_HTTP_PORT` в `.env`.

### Локальная установка зависимостей

Если хотите прогнать тесты или инструменты без полного стека:

```bash
cd backend && uv sync --all-groups && cd ..
cd frontend && npm install && cd ..
```

### Переменные окружения

Полный список — [`.env.example`](.env.example). Подробнее — в [docs/DEVELOPERS.md §11](docs/DEVELOPERS.md#11-настройки-и-переменные-окружения).

| Переменная                               | Зачем                                                                       |
| ---------------------------------------- | --------------------------------------------------------------------------- |
| `DJANGO_SECRET_KEY`                      | секрет Django; в production — сильное случайное значение                    |
| `DJANGO_DEBUG`                           | `true` в dev, `false` в prod (`mise run up`)                                |
| `DATABASE_URL`                           | PostgreSQL; по умолчанию `postgres://cadence:cadence@postgres:5432/cadence` |
| `CELERY_BROKER_URL`                      | RabbitMQ для Celery                                                         |
| `TELEGRAM_BOT_TOKEN`, `TELEGRAM_ENABLED` | опциональный бот и напоминания                                              |
| `CADENCE_TIME_ZONE`                      | таймзона проекта (rollover, quiet hours), по умолчанию `Europe/Moscow`      |
| `CSRF_TRUSTED_ORIGINS`                   | origins SPA для CSRF, например `http://localhost:8080`                      |

### Качество кода

```bash
mise run lint && mise run test
```

CI прогоняет ruff, mypy, pytest (≥85% coverage), vue-tsc, Vitest и production build. Конфиг: [`.github/workflows/ci.yml`](.github/workflows/ci.yml).

---

## Стек

<table>
  <tr>
    <td><strong>Backend</strong></td>
    <td>Django 6, DRF, drf-spectacular, PostgreSQL 17, Celery 5, aiogram 3</td>
  </tr>
  <tr>
    <td><strong>Frontend</strong></td>
    <td>Vue 3.5, TypeScript, Vite 6, Pinia, Tailwind 4, vue-i18n</td>
  </tr>
  <tr>
    <td><strong>Визуализация</strong></td>
    <td>ECharts 6, @vue-flow (редактор графа статусов)</td>
  </tr>
  <tr>
    <td><strong>Infra</strong></td>
    <td>Docker Compose, nginx, gunicorn, RabbitMQ, Flower (dev)</td>
  </tr>
  <tr>
    <td><strong>Quality</strong></td>
    <td>uv, ruff, mypy, pytest, Vitest, pre-commit</td>
  </tr>
</table>

<table>
  <tr>
    <td><strong>Почему Django</strong><br>зрелый ORM, admin, сессии, миграции и единый контур для доменных apps.</td>
    <td><strong>Почему Celery</strong><br>импорт inbox, напоминания, экспорт отчётов и rollover без блокировки API.</td>
    <td><strong>Почему Vue</strong><br>интерактивная доска, drag-and-drop, настройки workflow и аналитика в одном SPA.</td>
  </tr>
</table>

---

## Возможности

| Область      | Что умеет                                                |
| ------------ | -------------------------------------------------------- |
| **Доска**    | Kanban, DnD, drawer задачи, теги, приоритеты, story points; открытые задачи остаются на доске при смене ISO-недели |
| **Workflow** | схемы досок, граф статусов, правила переходов колонок    |
| **Ввод**     | UI, REST API (API key), JSON inbox, Telegram callbacks   |
| **Фон**      | Celery jobs с retry/cancel, Flower, service logs         |
| **Обзор**    | архив, week review, аналитика, экспорт CSV/XLSX/PDF      |
| **i18n**     | интерфейс RU / EN                                        |

Подробные потоки данных — в [docs/DEVELOPERS.md §6](docs/DEVELOPERS.md#6-потоки-данных).

---

## Архитектура

Проект — модульный монолит: доменные Django apps + Vue feature-модули.

| App             | Назначение                           |
| --------------- | ------------------------------------ |
| `boards`        | доска, схемы, колонки, граф статусов |
| `tasks`         | CRUD, move, close, события           |
| `weeks`         | ISO-недели, review, rollover         |
| `imports`       | JSON inbox с идемпотентностью        |
| `jobs`          | учёт фоновых заданий                 |
| `notifications` | Telegram-напоминания и callbacks     |
| `analytics`     | дашборды и экспорт                   |
| `archive`       | read-only архив задач                |
| `core`          | auth, settings, tags, platform       |

```text
cadence/
├── backend/apps/    boards · tasks · weeks · imports · jobs · …
├── frontend/src/    Vue SPA (features/)
├── infra/nginx/     reverse proxy
├── data/task-inbox/ JSON import pipeline
├── docs/            DEVELOPERS.md, openapi.json
└── logs/            service logs
```

### Общая схема

```mermaid
flowchart TB
    subgraph client["Клиент"]
        Browser["Браузер / API key"]
        Inbox["JSON inbox"]
        TG["Telegram"]
    end

    subgraph edge["Край"]
        Nginx["nginx :8080"]
    end

    subgraph app["Приложение"]
        SPA["Vue SPA"]
        API["Django API"]
        Bot["telegram-bot"]
    end

    subgraph data["Данные"]
        PG[("PostgreSQL")]
        MQ["RabbitMQ"]
        Worker["Celery"]
    end

    Browser --> Nginx --> SPA
    Nginx --> API
    API --> PG
    API --> MQ
    MQ --> Worker --> PG
    Inbox --> Worker
    TG --> Bot --> API
```

### Поток задачи (создание через API)

```mermaid
sequenceDiagram
  participant Client
  participant API as Django API
  participant Task as TaskCreationService
  participant DB as PostgreSQL
  participant Celery

  Client->>API: POST /api/v1/tasks/ (session или Api-Key)
  API->>Task: create(board, column, week, tags)
  Task->>DB: Task + TaskEvent
  Task->>Celery: schedule_next_reminder (если включено)
  API-->>Client: 201 + task JSON
```

nginx маршрутизирует `/` во frontend, `/api/` и `/admin/` в backend.

---

## API

База: `/api/v1/` через nginx (`http://localhost:8080/api/v1/…`).

| Метод       | Путь                         | Описание          |
| ----------- | ---------------------------- | ----------------- |
| `GET`       | `/api/health/`               | health check      |
| `POST`      | `/api/v1/auth/login/`        | вход (session)    |
| `GET`       | `/api/v1/board/`             | payload доски     |
| `GET\|POST` | `/api/v1/tasks/`             | список / создание |
| `POST`      | `/api/v1/tasks/<id>/move/`   | перемещение       |
| `POST`      | `/api/v1/tasks/<id>/close/`  | закрытие / архив  |
| `POST`      | `/api/v1/imports/upload/`    | загрузка JSON     |
| `GET`       | `/api/v1/jobs/`              | фоновые задания   |
| `GET`       | `/api/v1/analytics/summary/` | сводка аналитики  |
| `GET\|POST` | `/api/v1/analytics/exports/` | экспорт CSV/XLSX/PDF (фоновые job) |
| `GET`       | `/api/v1/analytics/exports/preview/` | предпросмотр макета экспорта |

Документация: [`/api/docs/`](http://localhost:8080/api/docs/) · снимок схемы: [`docs/openapi.json`](docs/openapi.json).

### Аутентификация

| Механизм    | Заголовок / способ               | Сценарий                    |
| ----------- | -------------------------------- | --------------------------- |
| **Session** | cookie после `POST /auth/login/` | браузер, SPA                |
| **API key** | `Authorization: Api-Key cd_…`    | скрипты, внешние интеграции |

Ключи выпускаются в Django Admin (`ApiKey.issue()`).

### Пример: создать задачу

```bash
curl -X POST http://localhost:8080/api/v1/tasks/ \
  -H "Authorization: Api-Key cd_YOUR_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Разобрать PR",
    "column_id": 1,
    "week": "2026-W12",
    "tags": ["backend"]
  }'
```

Полный список эндпоинтов — [docs/DEVELOPERS.md §9](docs/DEVELOPERS.md#9-api-обзор-эндпоинтов).

---

## Данные и логи

| Путь                              | Что хранится                               |
| --------------------------------- | ------------------------------------------ |
| `postgres_data` (volume)          | задачи, доски, недели, jobs, notifications |
| `data/task-inbox/pending/`        | входящие JSON для импорта                  |
| `data/task-inbox/processed/`      | успешно обработанные файлы                 |
| `media/exports/`                  | сгенерированные CSV/XLSX/PDF               |
| `logs/api.log`, `logs/worker.log` | service logs (`CADENCE_LOG_DIR`)           |

В UI: **Настройки → Общие → Service logs**. В dev доступен Flower на `:5556`.

---

## Тесты

```bash
mise run test
```

| Слой     | Инструмент         | Покрытие                                             |
| -------- | ------------------ | ---------------------------------------------------- |
| Backend  | pytest, ruff, mypy | ≥85% coverage (`apps/`), EC-тесты в `backend/tests/` |
| Frontend | vue-tsc, Vitest    | 19 spec-файлов, `npm run build`                      |

Отдельно:

```bash
cd backend && DJANGO_SETTINGS_MODULE=cadence.settings.test uv run pytest tests/test_ec_boards.py -v
cd frontend && npm run test -- --run
```

---

## Деплой

```bash
# .env
DJANGO_SECRET_KEY=<strong-random>
DJANGO_DEBUG=false
CSRF_TRUSTED_ORIGINS=https://your-domain.example
DJANGO_ALLOWED_HOSTS=your-domain.example

mise run up
```

Чеклист production — [docs/DEVELOPERS.md §14](docs/DEVELOPERS.md#14-production).

Текущий публичный демо-стенд: [Hugging Face Spaces](https://kudyasoft-cadence.hf.space/).

---

## Документация

| Тема                                         | Файл                                     |
| -------------------------------------------- | ---------------------------------------- |
| Архитектура, apps, потоки данных, разработка | [docs/DEVELOPERS.md](docs/DEVELOPERS.md) |
| История изменений                            | [CHANGELOG.md](CHANGELOG.md)             |
| OpenAPI snapshot                             | [docs/openapi.json](docs/openapi.json)   |
| Переменные окружения                         | [.env.example](.env.example)             |

---

<div align="center">

<sub>Cadence · v1.1.1 · Django · Vue · Celery · MIT</sub>

</div>
