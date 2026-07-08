from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import time
import webbrowser
from collections import deque
from collections.abc import Callable
from dataclasses import asdict, dataclass
from pathlib import Path
from urllib.error import HTTPError, URLError

from platformdirs import user_config_dir, user_log_dir

from .friendly_action import friendly_action_line
from .i18n import tr

ProgressCallback = Callable[[str], None]

APP_NAME = "cadence-launcher"
STACK_PROFILE = "prod"
DEFAULT_NGINX_PORT = "8080"
DEFAULT_PROD_SECRET = "local-prod-secret-key-for-mise-up-only"

PROD_SERVICES = [
    "postgres",
    "rabbitmq",
    "backend",
    "celery-worker",
    "celery-beat",
    "nginx",
]

SERVICE_LABELS = {
    "nginx": "nginx (prod)",
    "celery-worker": "celery worker",
    "celery-beat": "celery beat",
}

_active_stream_proc: subprocess.Popen[str] | None = None


class LauncherError(RuntimeError):
    """User-facing launcher error."""


@dataclass(slots=True)
class LauncherConfig:
    repo_root: str | None = None
    language: str | None = None


@dataclass(slots=True)
class ServiceStatus:
    name: str
    label: str
    state: str


@dataclass(slots=True)
class AppStatus:
    mode: str
    url: str
    api_ready: bool
    web_ready: bool
    services: list[ServiceStatus]


@dataclass(slots=True)
class RuntimePaths:
    repo_root: Path
    config_file: Path
    log_file: Path


def config_file_path() -> Path:
    config_home = Path(user_config_dir(APP_NAME))
    config_home.mkdir(parents=True, exist_ok=True)
    return config_home / "config.json"


def launcher_paths(repo_root: Path) -> RuntimePaths:
    log_home = Path(user_log_dir(APP_NAME))
    log_home.mkdir(parents=True, exist_ok=True)
    return RuntimePaths(
        repo_root=repo_root,
        config_file=config_file_path(),
        log_file=log_home / "launcher.log",
    )


def load_config() -> LauncherConfig:
    config_file = config_file_path()
    if not config_file.exists():
        return LauncherConfig()
    data = json.loads(config_file.read_text(encoding="utf-8"))
    repo_root = data.get("repo_root")
    language = data.get("language")
    return LauncherConfig(
        repo_root=repo_root if isinstance(repo_root, str) else None,
        language=language if isinstance(language, str) else None,
    )


def save_config(config: LauncherConfig) -> None:
    config_file = config_file_path()
    config_file.write_text(json.dumps(asdict(config), indent=2), encoding="utf-8")


def persist_language(language: str) -> None:
    from .i18n import set_locale

    config = load_config()
    config.language = language
    save_config(config)
    set_locale(language)


def log_message(repo_root: Path, message: str) -> None:
    log_file = launcher_paths(repo_root).log_file
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    with log_file.open("a", encoding="utf-8") as stream:
        stream.write(f"[{timestamp}] {message}\n")


def is_repo_root(path: Path) -> bool:
    return (
        path.is_dir()
        and (path / "docker-compose.yml").exists()
        and (path / "backend").is_dir()
        and (path / "frontend").is_dir()
    )


def discover_repo_root(start: Path | None = None) -> Path | None:
    env_root = os.getenv("CADENCE_ROOT")
    if env_root:
        candidate = Path(env_root).expanduser().resolve()
        if is_repo_root(candidate):
            return candidate

    config = load_config()
    if config.repo_root:
        candidate = Path(config.repo_root).expanduser().resolve()
        if is_repo_root(candidate):
            return candidate

    search_roots = [start or Path.cwd(), Path(__file__).resolve()]
    for root in search_roots:
        current = root.resolve()
        for candidate in (current, *current.parents):
            if is_repo_root(candidate):
                return candidate
    return None


def select_repo_root(repo_root: Path) -> None:
    if not is_repo_root(repo_root):
        raise LauncherError(tr("runtime.invalid_repo"))
    config = load_config()
    config.repo_root = str(repo_root.resolve())
    save_config(config)


def read_env_value(repo_root: Path, key: str, default: str) -> str:
    env_path = repo_root / ".env"
    if not env_path.exists():
        return default
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or not line.startswith(f"{key}="):
            continue
        value = line.split("=", 1)[1].strip().strip('"').strip("'")
        return value or default
    return default


def read_mise_env_value(repo_root: Path, key: str, default: str = "") -> str:
    mise_path = repo_root / ".mise.toml"
    if not mise_path.exists():
        return default
    for raw_line in mise_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or key not in line:
            continue
        marker = f'{key} = "'
        if marker not in line:
            continue
        return line.split(marker, 1)[1].split('"', 1)[0].strip() or default
    return default


def web_url(repo_root: Path) -> str:
    port = read_env_value(repo_root, "NGINX_HTTP_PORT", DEFAULT_NGINX_PORT)
    return f"http://localhost:{port}"


def health_url(repo_root: Path) -> str:
    return f"{web_url(repo_root)}/api/health/"


def compose_command(*args: str) -> list[str]:
    return ["docker", "compose", *args]


def run_command(
    command: list[str],
    *,
    cwd: Path,
    env: dict[str, str] | None = None,
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        command,
        cwd=cwd,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )
    if check and result.returncode != 0:
        stderr = result.stderr.strip() or result.stdout.strip() or "Command failed"
        raise LauncherError(stderr)
    return result


def cancel_streaming_command() -> None:
    global _active_stream_proc
    proc = _active_stream_proc
    if proc is None or proc.poll() is not None:
        return
    proc.terminate()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait()


def run_streaming_command(
    command: list[str],
    *,
    cwd: Path,
    env: dict[str, str] | None = None,
    progress: ProgressCallback | None = None,
) -> int:
    global _active_stream_proc
    proc = subprocess.Popen(
        command,
        cwd=cwd,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )
    _active_stream_proc = proc
    try:
        if proc.stdout is not None:
            for line in proc.stdout:
                if proc.poll() is not None and not line:
                    break
                stripped = line.strip()
                if not stripped:
                    continue
                if progress:
                    friendly = friendly_action_line(stripped)
                    if friendly:
                        progress(friendly)
        return proc.wait()
    finally:
        _active_stream_proc = None


def run_streaming_command_with_tail(
    command: list[str],
    *,
    cwd: Path,
    env: dict[str, str] | None = None,
    progress: ProgressCallback | None = None,
    tail_lines: int = 80,
) -> tuple[int, str]:
    """Run a streaming command and keep a small tail for error reporting."""
    tail: deque[str] = deque(maxlen=max(10, tail_lines))
    proc = subprocess.Popen(
        command,
        cwd=cwd,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )
    global _active_stream_proc
    _active_stream_proc = proc
    try:
        if proc.stdout is not None:
            for line in proc.stdout:
                if proc.poll() is not None and not line:
                    break
                stripped = line.strip()
                if not stripped:
                    continue
                tail.append(stripped)
                if progress:
                    friendly = friendly_action_line(stripped)
                    if friendly:
                        progress(friendly)
        code = proc.wait()
    finally:
        _active_stream_proc = None
    return code, "\n".join(tail)


def check_prerequisites(repo_root: Path) -> None:
    if shutil.which("docker") is None:
        raise LauncherError(tr("runtime.docker_missing"))
    if not is_repo_root(repo_root):
        raise LauncherError(tr("runtime.project_not_found", path=repo_root))
    run_command(["docker", "info"], cwd=repo_root)


def compose_ps_snapshot(repo_root: Path, profile: str) -> dict[str, tuple[str, str]]:
    result = run_command(
        compose_command("--profile", profile, "ps", "-a", "--format", "json"),
        cwd=repo_root,
        check=False,
    )
    snapshot: dict[str, tuple[str, str]] = {}
    for line in result.stdout.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        try:
            data = json.loads(stripped)
        except json.JSONDecodeError:
            continue
        service = data.get("Service", "")
        if not service:
            continue
        state = str(data.get("State", "unknown")).lower()
        health = str(data.get("Health", "none") or "none").lower()
        snapshot[service] = (state, health)
    return snapshot


def map_container_state(state: str, health: str) -> str:
    if state != "running":
        return state or "stopped"
    if health == "healthy":
        return "healthy"
    if health == "unhealthy":
        return "unhealthy"
    if health == "starting":
        return "starting"
    return "running"


def detect_mode(snapshot: dict[str, tuple[str, str]]) -> str:
    nginx = snapshot.get("nginx")
    if nginx and nginx[0] == "running":
        return STACK_PROFILE
    return "stopped"


def service_state_from_snapshot(
    snapshot: dict[str, tuple[str, str]],
    service: str,
) -> str:
    entry = snapshot.get(service)
    if entry is None:
        return "stopped"
    return map_container_state(*entry)


def service_label(service: str) -> str:
    return SERVICE_LABELS.get(service, service)


def probe_http(url: str, expect_json: bool = False) -> bool:
    try:
        from urllib.request import urlopen

        with urlopen(url, timeout=3) as response:
            if expect_json:
                response.read()
            return response.status in {200, 304}
    except (URLError, TimeoutError, HTTPError, OSError):
        return False


def api_ready(repo_root: Path) -> bool:
    return probe_http(health_url(repo_root), expect_json=True)


def web_ready(repo_root: Path) -> bool:
    return probe_http(f"{web_url(repo_root)}/")


def collect_status(repo_root: Path) -> AppStatus:
    snapshot = compose_ps_snapshot(repo_root, STACK_PROFILE)
    mode = detect_mode(snapshot)
    services = [
        ServiceStatus(
            name=service,
            label=service_label(service),
            state=service_state_from_snapshot(snapshot, service),
        )
        for service in PROD_SERVICES
    ]
    return AppStatus(
        mode=mode,
        url=web_url(repo_root),
        api_ready=api_ready(repo_root),
        web_ready=web_ready(repo_root),
        services=services,
    )


def stopped_status(repo_root: Path) -> AppStatus:
    return AppStatus(
        mode="stopped",
        url=web_url(repo_root),
        api_ready=False,
        web_ready=False,
        services=[
            ServiceStatus(name=service, label=service_label(service), state="stopped")
            for service in PROD_SERVICES
        ],
    )


def resolve_secret_key(repo_root: Path) -> tuple[str, bool]:
    env_key = os.getenv("DJANGO_SECRET_KEY")
    if env_key and env_key != "change-me":
        return env_key, False
    file_key = read_env_value(repo_root, "DJANGO_SECRET_KEY", "")
    if file_key and file_key != "change-me":
        return file_key, False
    mise_key = read_mise_env_value(repo_root, "DJANGO_SECRET_KEY", DEFAULT_PROD_SECRET)
    if mise_key and mise_key != "change-me":
        return mise_key, True
    raise LauncherError(tr("runtime.secret_required"))


def prod_env(repo_root: Path) -> dict[str, str]:
    secret_key, using_fallback = resolve_secret_key(repo_root)
    if using_fallback:
        log_message(repo_root, tr("runtime.secret_fallback"))
    env = os.environ.copy()
    env.update(
        {
            "DJANGO_SETTINGS_MODULE": "cadence.settings.prod",
            "DJANGO_DEBUG": "false",
            "GUNICORN_EXTRA_ARGS": "--workers 2",
            "DJANGO_SECRET_KEY": secret_key,
        }
    )
    return env


def has_prod_containers(snapshot: dict[str, tuple[str, str]]) -> bool:
    return any(service in snapshot for service in PROD_SERVICES)


def compose_down(repo_root: Path, progress: ProgressCallback | None = None) -> int:
    return run_streaming_command(
        compose_command("--profile", STACK_PROFILE, "down"),
        cwd=repo_root,
        progress=progress,
    )


def wait_until_stopped(repo_root: Path, *, timeout: int = 60) -> None:
    start_time = time.monotonic()
    while True:
        if not has_prod_containers(compose_ps_snapshot(repo_root, STACK_PROFILE)):
            return
        if int(time.monotonic() - start_time) >= timeout:
            raise LauncherError(tr("runtime.stop_failed", code="timeout"))
        time.sleep(1)


def prepare_clean_start(
    repo_root: Path,
    progress: ProgressCallback | None = None,
) -> None:
    if progress:
        progress(tr("runtime.prep_stop"))
    code = compose_down(repo_root, progress)
    if code != 0:
        raise LauncherError(tr("runtime.stop_failed", code=code))
    wait_until_stopped(repo_root)
    log_message(repo_root, "Stack stopped before start")


def rollback_stack(repo_root: Path, progress: ProgressCallback | None = None) -> None:
    if progress:
        progress(tr("runtime.rollback"))
    code = compose_down(repo_root, progress)
    if code == 0:
        log_message(repo_root, "Stack rolled back after failed start")
    else:
        log_message(repo_root, f"Rollback failed (code {code})")


def start_stack(repo_root: Path, progress: ProgressCallback | None = None) -> None:
    check_prerequisites(repo_root)
    snapshot = compose_ps_snapshot(repo_root, STACK_PROFILE)
    current_mode = detect_mode(snapshot)
    if current_mode == STACK_PROFILE:
        status = collect_status(repo_root)
        if status.api_ready and status.web_ready:
            if progress:
                progress(tr("runtime.already_running"))
            return
        try:
            wait_until_ready(repo_root, progress=progress)
        except LauncherError:
            rollback_stack(repo_root, progress)
            raise
        return

    if has_prod_containers(snapshot):
        prepare_clean_start(repo_root, progress)

    if progress:
        progress(tr("runtime.starting"))

    try:
        code, tail = run_streaming_command_with_tail(
            compose_command("--profile", STACK_PROFILE, "up", "-d", "--build"),
            cwd=repo_root,
            env=prod_env(repo_root),
            progress=progress,
        )
        if code != 0:
            details = tr("runtime.start_failed", code=code)
            if tail:
                details = f"{details}\n\n{tail}"
            raise LauncherError(details)

        wait_until_ready(repo_root, progress=progress)
        log_message(repo_root, "Stack started in prod mode")
    except LauncherError:
        rollback_stack(repo_root, progress)
        raise


def stop_stack(repo_root: Path, progress: ProgressCallback | None = None) -> None:
    check_prerequisites(repo_root)
    snapshot = compose_ps_snapshot(repo_root, STACK_PROFILE)
    if not has_prod_containers(snapshot):
        if progress:
            progress(tr("runtime.already_stopped"))
        return
    if progress:
        progress(tr("runtime.stopping"))
    code = compose_down(repo_root, progress)
    if code != 0:
        raise LauncherError(tr("runtime.stop_failed", code=code))
    log_message(
        repo_root,
        "Stack stopped (prod profile only; dev containers are left untouched)",
    )


def wait_until_ready(
    repo_root: Path,
    *,
    timeout: int = 360,
    progress: ProgressCallback | None = None,
) -> None:
    start_time = time.monotonic()
    while True:
        if int(time.monotonic() - start_time) >= timeout:
            raise LauncherError(tr("runtime.timeout"))

        status = collect_status(repo_root)
        ready_count = sum(
            1 for service in status.services if service.state in {"healthy", "running"}
        )
        total_count = len(status.services)
        if progress:
            progress(tr("runtime.progress_ready", ready=ready_count, total=total_count))

        critical_ready = all(
            service.state in {"healthy", "running"}
            for service in status.services
            if service.name in {"postgres", "rabbitmq", "backend"}
        )

        if status.api_ready and status.web_ready and critical_ready:
            if progress:
                progress(tr("runtime.all_ready"))
            return
        time.sleep(2)


def open_in_browser(repo_root: Path) -> None:
    url = web_url(repo_root)
    if sys.platform.startswith("linux"):
        opener = shutil.which("xdg-open")
        if opener:
            subprocess.Popen(
                [opener, url],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
            )
        else:
            webbrowser.open(url)
    elif sys.platform == "darwin":
        subprocess.Popen(
            ["open", url],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
    elif sys.platform == "win32":
        os.startfile(url)
    else:
        webbrowser.open(url)
    log_message(repo_root, f"Open browser: {url}")
