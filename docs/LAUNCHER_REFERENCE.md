# Справочник Cadence Launcher

Кроссплатформенный desktop launcher (**alpha**, `0.9.1a1`) в [`tools/launcher`](../tools/launcher) для production-like Docker-стека Cadence.

Поддерживаемые платформы: Linux, macOS, Windows (PySide6 + Docker Compose v2).

## Статус и назначение

- Launcher находится в **alpha**: API, UX и packaging могут меняться без semver-гарантий основного проекта Cadence.
- Версия launcher (`0.9.1a1`) **не совпадает** с версией проекта (`v1.2.0` и далее).
- Launcher не заменяет `mise run dev` для разработки: он ориентирован на production-like запуск через `docker compose --profile prod`.

## Область ответственности

- **Только prod-профиль** — `docker compose --profile prod`
- Нет dev-режима, Flower, HMR-frontend и nginx-dev
- Нет встроенного просмотра compose-логов (в отличие от старого GTK launcher с zenity)
- Нет отдельного release-тега launcher: артефакты собираются workflow `Launcher Build`, теги проекта (`v*`) к launcher не привязаны

## Зависимости

| Компонент | Зачем |
| --- | --- |
| Docker + Docker Compose v2 | запуск и остановка стека |
| Локальный clone репозитория Cadence | launcher работает с `docker-compose.yml` в корне проекта |
| Python 3.12+ и `uv` | запуск из исходников |
| PySide6 | UI (подтягивается через `uv sync`) |

Перед стартом launcher проверяет:

1. `docker` доступен в `PATH`
2. выбранный путь — валидный корень Cadence (`docker-compose.yml`, `backend/`, `frontend/`)
3. `docker info` завершается успешно (демон запущен)

## Действия в UI

| Кнопка | Поведение |
| --- | --- |
| **Start** | `docker compose --profile prod up -d --build` с prod-окружением |
| **Stop** | `docker compose --profile prod down` |
| **Open** | открывает `http://localhost:<NGINX_HTTP_PORT>` в браузере |

Дополнительно:

- опрос статуса каждые **3 с** в idle-режиме
- во время Start/Stop кнопки и переключатель языка блокируются
- при ошибке Start UI сбрасывается в состояние «всё остановлено»

**Stop** затрагивает только prod-профиль. Dev-контейнеры, поднятые отдельно (`mise run dev`, ручной compose), не удаляются.

## Модель режима

| Режим | Условие |
| --- | --- |
| `stopped` | prod-контейнер `nginx` не запущен |
| `prod` | prod-контейнер `nginx` в состоянии `running` |

## Сервисы prod-стека

| Сервис | Подпись в UI |
| --- | --- |
| postgres | postgres |
| rabbitmq | rabbitmq |
| backend | backend |
| celery-worker | celery worker |
| celery-beat | celery beat |
| nginx | nginx (prod) |

## Состояния сервисов

Источник: один снимок `docker compose ps -a --format json` на каждый опрос (без отдельного `docker inspect` на сервис).

Допустимые состояния: `healthy`, `running`, `starting`, `unhealthy`, `stopped`, `unknown`.

Отображение в бейджах:

| Состояние | Семантика |
| --- | --- |
| `healthy`, `running` | ok |
| `starting` | ожидание |
| `unhealthy` | ошибка |
| `stopped`, `unknown` | нейтрально |

## Готовность стека

Стек считается готовым, когда одновременно:

- `GET /api/health/` отвечает успешно
- корень веб-приложения отвечает `200` или `304`
- `postgres`, `rabbitmq`, `backend` в состоянии `healthy` или `running`

Ожидание готовности после Start: до **360 с**, опрос каждые **2 с**.

## Запуск (runtime)

### Если стек уже поднимается

Если prod уже активен, но API/Web ещё не готовы, launcher **ждёт готовности**, а не перезапускает стек с нуля.

### Если остались частичные prod-контейнеры

Перед `up` выполняется `compose down` и ожидание полной остановки prod-контейнеров.

### Ошибка Start

При сбое `up` или таймауте готовности launcher:

1. вызывает `docker compose --profile prod down` (rollback)
2. показывает диалог с кодом ошибки и хвостом compose-вывода
3. сбрасывает UI в `stopped`

### Prod-окружение, которое подставляет launcher

| Переменная | Значение |
| --- | --- |
| `DJANGO_SETTINGS_MODULE` | `cadence.settings.prod` |
| `DJANGO_DEBUG` | `false` |
| `GUNICORN_EXTRA_ARGS` | `--workers 2` |
| `DJANGO_SECRET_KEY` | см. ниже |

### Разрешение `DJANGO_SECRET_KEY`

Порядок:

1. переменная окружения `DJANGO_SECRET_KEY` (если не `change-me`)
2. значение из `.env` репозитория
3. значение из `.mise.toml`
4. локальный fallback `local-prod-secret-key-for-mise-up-only` с записью предупреждения в лог

Если ни один источник не дал валидный ключ, Start завершается ошибкой.

## Конфигурация launcher

Хранится в user config dir (`platformdirs.user_config_dir("cadence-launcher")`):

- Linux: `~/.config/cadence-launcher/config.json`
- путь не зависит от текущей рабочей директории shell

Поля:

| Поле | Описание |
| --- | --- |
| `repo_root` | путь к корню репозитория Cadence |
| `language` | `en` или `ru` |

Порядок поиска корня репозитория:

1. `CADENCE_ROOT`
2. сохранённый `repo_root` в config
3. обход родителей от `cwd` и расположения пакета

Если корень не найден, при первом запуске открывается диалог выбора папки.

### Локализация

- по умолчанию: английский
- русский: если системная локаль русская, задан `CADENCE_LAUNCHER_LANG=ru`, или выбран **RU** в заголовке окна
- выбор языка сохраняется в config

### Логи launcher

Файл: user log dir / `launcher.log` (через `platformdirs.user_log_dir`).

Туда пишутся ключевые события: старт/стоп, rollback, открытие браузера, предупреждения о secret key.

## Параметры Cadence из репозитория

| Параметр | Источник | По умолчанию |
| --- | --- | --- |
| `NGINX_HTTP_PORT` | `.env` | `8080` |
| `DJANGO_SECRET_KEY` | env / `.env` / `.mise.toml` | см. выше |

## UI

### Окно

- заголовок: `Cadence`
- имя приложения (в системе): `Cadence Launcher (alpha)`
- размер: `400×560`, ширина фиксирована
- при Start/Stop высота плавно увеличивается для панели активности
- окно центрируется на экране при первом показе

### Блоки

- splash overlay (проверка окружения + первичный статус)
- header (иконка, статус, переключатель EN/RU)
- actions (Start/Stop, Open)
- список сервисов с бейджами состояния
- activity panel (шаг, прогресс, elapsed) во время Start/Stop

### Визуальные токены

| Токен | Значение |
| --- | --- |
| Фон приложения | `#e8ebf1` |
| Карточки | `#ffffff`, border `#d0d6e0` |
| Акцент | `#5b6ee8` |
| Running-текст | `#2563eb` |
| Приглушённый текст | `#8b95a8` |
| Заголовок | `#161b26` |
| Ошибка | `#dc2626` / `#b91c1c` |
| Поверхность строки | `#f4f6f9` |

Шрифт: `Inter, Cantarell, Ubuntu, sans-serif`

## Структура модулей

```text
cadence_launcher/
  app.py             — entry, palette, выбор repo root, run()
  runtime.py         — Docker orchestration, config, status, secret key
  workers.py         — фоновые QRunnable-задачи
  friendly_action.py — compose log → понятный шаг для UI
  i18n.py            — строки en/ru
  ui/
    constants.py     — размеры окна, иконки состояний
    styles.py        — QSS
    widgets.py       — SpinnerWidget, ActivityRevealer, …
    window.py        — LauncherWindow
```

## Запуск из исходников

```bash
cd tools/launcher
uv sync --extra dev
uv run cadence-launcher
```

## Сборка portable bundle

Сборка native, только на целевой ОС:

```bash
cd tools/launcher
uv sync --extra build
uv run python scripts/build.py
```

Результат в `tools/launcher/dist/`:

- `CadenceLauncher-linux.zip`
- `CadenceLauncher-macos.zip`
- `CadenceLauncher-windows.zip`

Иконки подхватываются из `assets/` при наличии: `cadence.ico`, `cadence.icns`, `cadence.png`, `cadence.svg`.

На каждом push/PR в `develop`/`main` job **Launcher** в [`/.github/workflows/ci.yml`](../.github/workflows/ci.yml) запускает `pytest` для `tools/launcher` (unit-тесты runtime/i18n, без GUI и Docker).

Workflow [`/.github/workflows/launcher.yml`](../.github/workflows/launcher.yml) сначала прогоняет те же тесты, затем собирает артефакты на `ubuntu-latest`, `macos-latest`, `windows-latest` по публикации релиза проекта или вручную (`workflow_dispatch`). Отдельные теги `launcher-v*` не используются.

## Старый GTK launcher (для сравнения)

Linux-only предшественник: `cadence-gui.py`, `cadence.sh` — переключение dev/prod, 8 dev-сервисов, просмотр логов через zenity.

Новый launcher сохраняет похожий визуальный язык, но:

- кроссплатформенный (Qt)
- только prod orchestration
- без встроенного log viewer
- с rollback при ошибке Start и batched status polling
