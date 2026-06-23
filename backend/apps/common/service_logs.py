from __future__ import annotations

import re
from collections import deque
from dataclasses import asdict, dataclass
from pathlib import Path
from threading import Lock
from typing import Literal

from django.utils import timezone as dj_timezone

from cadence.settings.environment import env, repo_root

ServiceId = Literal["api", "database", "broker", "worker"]
LogSource = Literal["process", "health", "jobs", "file"]

SERVICE_IDS: tuple[ServiceId, ...] = ("api", "database", "broker", "worker")
MAX_BUFFER = 400

_buffers: dict[str, deque[ServiceLogEntry]] = {
    service_id: deque(maxlen=MAX_BUFFER) for service_id in SERVICE_IDS
}
_lock = Lock()

LOG_LINE_RE = re.compile(
    r"^(?:\[(?P<bracket_at>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\]|"
    r"(?P<logged_at>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3})) (?P<level>\w+) "
)


@dataclass(frozen=True)
class ServiceLogEntry:
    logged_at: str
    level: str
    message: str
    source: LogSource
    job_id: int | None = None


def log_dir() -> Path:
    return Path(env.str("CADENCE_LOG_DIR", default=str(repo_root() / "logs")))


def log_file_path(service_id: str) -> Path:
    return log_dir() / f"{service_id}.log"


def record_service_log(
    service_id: str,
    level: str,
    message: str,
    *,
    source: LogSource = "process",
    logged_at: str | None = None,
) -> None:
    if service_id not in _buffers:
        return
    entry = ServiceLogEntry(
        logged_at=logged_at or dj_timezone.now().isoformat(),
        level=level.upper(),
        message=message,
        source=source,
    )
    with _lock:
        _buffers[service_id].append(entry)


def record_health_check(
    service_id: str,
    *,
    status: str,
    latency_ms: int = 0,
    detail: str = "",
) -> None:
    level = "INFO" if status == "ok" else "WARNING" if status == "degraded" else "ERROR"
    parts = [f"Health check: {status}"]
    if latency_ms > 0:
        parts.append(f"{latency_ms} ms")
    if detail:
        parts.append(detail)
    record_service_log(service_id, level, " — ".join(parts), source="health")


def _parse_log_line(line: str) -> ServiceLogEntry:
    match = LOG_LINE_RE.match(line)
    if match:
        logged_at = match.group("logged_at") or match.group("bracket_at") or ""
        return ServiceLogEntry(
            logged_at=logged_at,
            level=match.group("level"),
            message=line,
            source="file",
        )
    return ServiceLogEntry(logged_at="", level="INFO", message=line, source="file")


def tail_log_file(service_id: str, *, limit: int) -> list[ServiceLogEntry]:
    path = log_file_path(service_id)
    if not path.is_file():
        return []
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return []
    return [_parse_log_line(line) for line in lines[-limit:]]


def log_file_exists(service_id: str) -> bool:
    return log_file_path(service_id).is_file()


def _worker_job_logs(*, limit: int) -> list[ServiceLogEntry]:
    from apps.jobs.models import BackgroundJob

    jobs = list(BackgroundJob.objects.order_by("-created_at")[:limit])
    entries: list[ServiceLogEntry] = []
    for job in reversed(jobs):
        timestamp = job.finished_at or job.started_at or job.created_at
        if job.status == "failed" and job.last_error:
            level = "ERROR"
            message = f"Job #{job.id} {job.job_type} failed: {job.last_error[:500]}"
        elif job.status == "succeeded":
            level = "INFO"
            message = f"Job #{job.id} {job.job_type} succeeded"
        elif job.status == "processing":
            level = "INFO"
            message = (
                f"Job #{job.id} {job.job_type} processing "
                f"(attempt {job.attempts}/{job.max_attempts})"
            )
        else:
            level = "INFO"
            message = f"Job #{job.id} {job.job_type} {job.status}"
        entries.append(
            ServiceLogEntry(
                logged_at=timestamp.isoformat(),
                level=level,
                message=message,
                source="jobs",
                job_id=job.id,
            ),
        )
    return entries


def _buffer_entries(service_id: str) -> list[ServiceLogEntry]:
    with _lock:
        return list(_buffers.get(service_id, []))


def _sort_key(entry: ServiceLogEntry) -> str:
    if entry.logged_at:
        return entry.logged_at
    return ""


def get_service_logs(service_id: str, *, limit: int = 200) -> list[dict]:
    if service_id not in SERVICE_IDS:
        msg = f"Unknown service: {service_id}"
        raise ValueError(msg)

    limit = max(1, min(limit, 500))
    entries: list[ServiceLogEntry] = []
    entries.extend(_buffer_entries(service_id))
    entries.extend(tail_log_file(service_id, limit=limit))
    if service_id == "worker":
        entries.extend(_worker_job_logs(limit=min(50, limit)))

    seen: set[tuple[str, str]] = set()
    unique: list[ServiceLogEntry] = []
    for entry in entries:
        key = (entry.logged_at, entry.message)
        if key in seen:
            continue
        seen.add(key)
        unique.append(entry)

    unique.sort(key=_sort_key, reverse=True)
    return [asdict(entry) for entry in unique[:limit]]
