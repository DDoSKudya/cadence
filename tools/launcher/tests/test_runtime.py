from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from cadence_launcher.friendly_action import friendly_action_line, strip_ansi
from cadence_launcher.i18n import init_locale, tr
from cadence_launcher.runtime import (
    DEFAULT_PROD_SECRET,
    STACK_PROFILE,
    AppStatus,
    LauncherConfig,
    LauncherError,
    compose_ps_snapshot,
    detect_mode,
    discover_repo_root,
    is_repo_root,
    load_config,
    map_container_state,
    read_env_value,
    read_mise_env_value,
    resolve_secret_key,
    save_config,
    select_repo_root,
    service_state_from_snapshot,
    start_stack,
    stopped_status,
)


def test_is_repo_root_requires_expected_layout(tmp_path: Path) -> None:
    (tmp_path / "docker-compose.yml").write_text("services: {}\n", encoding="utf-8")
    (tmp_path / "backend").mkdir()
    (tmp_path / "frontend").mkdir()

    assert is_repo_root(tmp_path) is True


def test_read_env_value_falls_back_to_default(tmp_path: Path) -> None:
    assert read_env_value(tmp_path, "NGINX_HTTP_PORT", "8080") == "8080"


def test_read_env_value_reads_last_value_shape(tmp_path: Path) -> None:
    (tmp_path / ".env").write_text('NGINX_HTTP_PORT="9090"\n', encoding="utf-8")

    assert read_env_value(tmp_path, "NGINX_HTTP_PORT", "8080") == "9090"


def test_discover_repo_root_from_search_path(tmp_path: Path) -> None:
    repo_root = tmp_path / "cadence"
    repo_root.mkdir()
    (repo_root / "docker-compose.yml").write_text("services: {}\n", encoding="utf-8")
    (repo_root / "backend").mkdir()
    (repo_root / "frontend").mkdir()
    nested = repo_root / "tools" / "launcher"
    nested.mkdir(parents=True)

    assert discover_repo_root(nested) == repo_root


def test_map_container_state() -> None:
    assert map_container_state("running", "healthy") == "healthy"
    assert map_container_state("running", "starting") == "starting"
    assert map_container_state("running", "none") == "running"
    assert map_container_state("exited", "none") == "exited"
    assert map_container_state("", "none") == "stopped"


def test_detect_mode_from_snapshot() -> None:
    assert detect_mode({}) == "stopped"
    assert detect_mode({"nginx": ("running", "healthy")}) == STACK_PROFILE
    assert detect_mode({"nginx": ("exited", "none")}) == "stopped"


def test_service_state_from_snapshot() -> None:
    snapshot = {"postgres": ("running", "healthy")}
    assert service_state_from_snapshot(snapshot, "postgres") == "healthy"
    assert service_state_from_snapshot(snapshot, "rabbitmq") == "stopped"


def test_compose_ps_snapshot_parses_json_lines(tmp_path: Path) -> None:
    payload = (
        '{"Service":"nginx","State":"running","Health":"healthy"}\n'
        '{"Service":"postgres","State":"running","Health":"starting"}\n'
    )

    def fake_run(command, *, cwd, env=None, check=True):
        from types import SimpleNamespace

        return SimpleNamespace(returncode=0, stdout=payload, stderr="")

    with patch("cadence_launcher.runtime.run_command", side_effect=fake_run):
        snapshot = compose_ps_snapshot(tmp_path, STACK_PROFILE)

    assert snapshot["nginx"] == ("running", "healthy")
    assert snapshot["postgres"] == ("running", "starting")


def test_resolve_secret_key_prefers_env(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("DJANGO_SECRET_KEY", "from-env")
    key, fallback = resolve_secret_key(tmp_path)
    assert key == "from-env"
    assert fallback is False


def test_resolve_secret_key_reads_dotenv(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("DJANGO_SECRET_KEY", raising=False)
    (tmp_path / ".env").write_text('DJANGO_SECRET_KEY="from-file"\n', encoding="utf-8")
    key, fallback = resolve_secret_key(tmp_path)
    assert key == "from-file"
    assert fallback is False


def test_read_mise_env_value_reads_task_env(tmp_path: Path) -> None:
    (tmp_path / ".mise.toml").write_text(
        '[tasks.up]\nenv = { DJANGO_SECRET_KEY = "from-mise" }\n',
        encoding="utf-8",
    )
    assert read_mise_env_value(tmp_path, "DJANGO_SECRET_KEY") == "from-mise"


def test_resolve_secret_key_fallback(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("DJANGO_SECRET_KEY", raising=False)
    key, fallback = resolve_secret_key(tmp_path)
    assert key == DEFAULT_PROD_SECRET
    assert fallback is True


def test_resolve_secret_key_ignores_change_me_in_dotenv(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("DJANGO_SECRET_KEY", raising=False)
    (tmp_path / ".env").write_text('DJANGO_SECRET_KEY="change-me"\n', encoding="utf-8")
    (tmp_path / ".mise.toml").write_text(
        '[tasks.up]\nenv = { DJANGO_SECRET_KEY = "from-mise" }\n',
        encoding="utf-8",
    )
    key, fallback = resolve_secret_key(tmp_path)
    assert key == "from-mise"
    assert fallback is True


def test_select_repo_root_preserves_language(tmp_path: Path) -> None:
    (tmp_path / "docker-compose.yml").write_text("services: {}\n", encoding="utf-8")
    (tmp_path / "backend").mkdir()
    (tmp_path / "frontend").mkdir()

    config_file = tmp_path / "config.json"
    with patch("cadence_launcher.runtime.config_file_path", return_value=config_file):
        save_config(LauncherConfig(language="ru"))
        select_repo_root(tmp_path)
        saved = load_config()

    assert saved.repo_root == str(tmp_path.resolve())
    assert saved.language == "ru"


def test_config_uses_fixed_path_not_cwd(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config_file = tmp_path / "config.json"
    with patch("cadence_launcher.runtime.config_file_path", return_value=config_file):
        save_config(LauncherConfig(repo_root="/tmp/cadence", language="en"))
        other = tmp_path / "nested"
        other.mkdir()
        monkeypatch.chdir(other)
        loaded = load_config()
    assert loaded.repo_root == "/tmp/cadence"
    assert loaded.language == "en"


def test_friendly_action_line_service_ready() -> None:
    init_locale("en")
    line = friendly_action_line("cadence-postgres-1  Healthy")
    assert "postgres" in line.lower()
    assert "ready" in line.lower()


def test_friendly_action_line_strips_ansi() -> None:
    assert strip_ansi("\x1b[32mok\x1b[0m") == "ok"


def test_friendly_action_line_building() -> None:
    init_locale("en")
    assert tr("friendly.building") in friendly_action_line("Building backend")


def _minimal_repo(tmp_path: Path) -> Path:
    (tmp_path / "docker-compose.yml").write_text("services: {}\n", encoding="utf-8")
    (tmp_path / "backend").mkdir()
    (tmp_path / "frontend").mkdir()
    return tmp_path


def test_start_stack_rolls_back_when_compose_up_fails(tmp_path: Path) -> None:
    repo = _minimal_repo(tmp_path)
    rollback_commands: list[list[str]] = []

    def fake_down(repo_root, progress=None):
        rollback_commands.append(
            ["docker", "compose", "--profile", STACK_PROFILE, "down"]
        )
        return 0

    def fake_up(command, *, cwd, env=None, progress=None, tail_lines=80):
        return 1, "compose up failed"

    with (
        patch("cadence_launcher.runtime.check_prerequisites"),
        patch("cadence_launcher.runtime.compose_ps_snapshot", return_value={}),
        patch("cadence_launcher.runtime.compose_down", side_effect=fake_down),
        patch(
            "cadence_launcher.runtime.run_streaming_command_with_tail",
            side_effect=fake_up,
        ),
    ):
        with pytest.raises(LauncherError, match="Failed to start"):
            start_stack(repo)

    assert rollback_commands
    assert "down" in rollback_commands[0]


def test_start_stack_rolls_back_on_readiness_timeout(tmp_path: Path) -> None:
    repo = _minimal_repo(tmp_path)
    rollback_commands: list[list[str]] = []

    def fake_down(repo_root, progress=None):
        rollback_commands.append(
            ["docker", "compose", "--profile", STACK_PROFILE, "down"]
        )
        return 0

    def fake_up(command, *, cwd, env=None, progress=None, tail_lines=80):
        return 0, ""

    ticks = iter([0.0, 400.0])

    def fake_monotonic() -> float:
        return next(ticks, 400.0)

    with (
        patch("cadence_launcher.runtime.check_prerequisites"),
        patch(
            "cadence_launcher.runtime.compose_ps_snapshot",
            return_value={"nginx": ("running", "starting")},
        ),
        patch("cadence_launcher.runtime.collect_status") as collect_status_mock,
        patch("cadence_launcher.runtime.compose_down", side_effect=fake_down),
        patch(
            "cadence_launcher.runtime.run_streaming_command_with_tail",
            side_effect=fake_up,
        ),
        patch("cadence_launcher.runtime.time.sleep"),
        patch("cadence_launcher.runtime.time.monotonic", side_effect=fake_monotonic),
    ):
        from cadence_launcher.runtime import AppStatus, ServiceStatus

        collect_status_mock.return_value = AppStatus(
            mode=STACK_PROFILE,
            url="http://localhost:8080",
            api_ready=False,
            web_ready=False,
            services=[ServiceStatus("nginx", "nginx (prod)", "starting")],
        )
        with pytest.raises(LauncherError, match="Timed out"):
            start_stack(repo)

    assert rollback_commands


def test_start_stack_restarts_partial_stack_before_up(tmp_path: Path) -> None:
    repo = _minimal_repo(tmp_path)
    stream_sequence: list[str] = []

    def fake_down(repo_root, progress=None):
        stream_sequence.append("down")
        return 0

    def fake_up(command, *, cwd, env=None, progress=None, tail_lines=80):
        stream_sequence.append("up")
        return 0, ""

    ready = AppStatus(
        mode=STACK_PROFILE,
        url="http://localhost:8080",
        api_ready=True,
        web_ready=True,
        services=[],
    )

    with (
        patch("cadence_launcher.runtime.check_prerequisites"),
        patch(
            "cadence_launcher.runtime.compose_ps_snapshot",
            return_value={"postgres": ("exited", "none")},
        ),
        patch("cadence_launcher.runtime.collect_status", return_value=ready),
        patch("cadence_launcher.runtime.compose_down", side_effect=fake_down),
        patch(
            "cadence_launcher.runtime.run_streaming_command_with_tail",
            side_effect=fake_up,
        ),
        patch("cadence_launcher.runtime.wait_until_stopped"),
        patch("cadence_launcher.runtime.time.sleep"),
    ):
        start_stack(repo)

    assert stream_sequence == ["down", "up"]


def test_start_stack_waits_when_prod_is_already_starting(tmp_path: Path) -> None:
    repo = _minimal_repo(tmp_path)
    pending = AppStatus(
        mode=STACK_PROFILE,
        url="http://localhost:8080",
        api_ready=False,
        web_ready=False,
        services=[],
    )

    with (
        patch(
            "cadence_launcher.runtime.compose_ps_snapshot",
            return_value={"nginx": ("running", "starting")},
        ),
        patch("cadence_launcher.runtime.collect_status", return_value=pending),
        patch("cadence_launcher.runtime.wait_until_ready") as wait_mock,
        patch("cadence_launcher.runtime.run_streaming_command_with_tail") as up_mock,
        patch("cadence_launcher.runtime.check_prerequisites"),
    ):
        start_stack(repo)

    wait_mock.assert_called_once()
    up_mock.assert_not_called()


def test_stopped_status_marks_all_services_stopped(tmp_path: Path) -> None:
    repo = _minimal_repo(tmp_path)
    status = stopped_status(repo)
    assert status.mode == "stopped"
    assert status.api_ready is False
    assert status.web_ready is False
    assert len(status.services) == 6
    assert all(service.state == "stopped" for service in status.services)
