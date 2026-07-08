# Cadence Launcher

Кроссплатформенный desktop launcher (**alpha**, `0.9.1a1`) для **production** Docker-стека Cadence.

## Назначение

- Компактный UI в духе оригинального Linux GTK launcher
- Linux, macOS и Windows на PySide6
- Portable-сборки для запуска двойным кликом (PyInstaller)
- Запуск и остановка prod-стека без shell-зависимостей на рабочем столе

**Вне scope:** dev-режим, просмотр логов в приложении, Flower, dev frontend/nginx-dev. Для разработки используйте `mise run dev`.

## Запуск из исходников

```bash
cd tools/launcher
uv sync --extra dev
uv run cadence-launcher
```

Язык: по умолчанию английский. Русский — если системная локаль русская или задан `CADENCE_LAUNCHER_LANG=ru`. Переключатель **EN / RU** в заголовке окна; выбор сохраняется в конфиге launcher.

## Конфигурация

Путь к конфигу: user config dir ОС (`~/.config/cadence-launcher/config.json` на Linux). Не зависит от текущей рабочей директории shell.

Задайте `CADENCE_ROOT` или выберите папку репозитория при первом запуске. Опционально `DJANGO_SECRET_KEY` в `.env` репозитория или в окружении (если ключ не найден, launcher пишет предупреждение в лог).

## Локальная сборка bundle

```bash
cd tools/launcher
uv sync --extra build
uv run python scripts/build.py
```

PyInstaller собирает native bundle, поэтому сборку нужно запускать на целевой ОС:

- Linux → `CadenceLauncher-linux.zip`
- macOS → `CadenceLauncher-macos.zip`
- Windows → `CadenceLauncher-windows.zip`

Артефакты попадают в `tools/launcher/dist/`. Workflow `Launcher Build` сначала прогоняет тесты, затем собирает bundle на `ubuntu-latest`, `macos-latest` и `windows-latest`. На каждом push/PR основной workflow `CI` также запускает `pytest` для launcher на Ubuntu.

Если в `assets/` появятся платформенные иконки (`cadence.ico`, `cadence.icns`, `cadence.png`), build-скрипт подхватит их автоматически. Без них launcher всё равно собирается и запускается с иконкой по умолчанию.

## Поведение Stop

`Stop` выполняет только `docker compose --profile prod down`. Контейнеры dev-стека, поднятого отдельно, не удаляются.

Полный контракт — в [LAUNCHER_REFERENCE.md](../../docs/LAUNCHER_REFERENCE.md). История версий — в [CHANGELOG.md](CHANGELOG.md).
