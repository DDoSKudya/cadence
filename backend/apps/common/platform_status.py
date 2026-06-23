from __future__ import annotations

import time
from contextlib import suppress
from dataclasses import asdict, dataclass
from typing import Literal
from zoneinfo import ZoneInfo

from django.conf import settings
from django.db import connection
from django.utils import timezone as dj_timezone

from apps.common.service_logs import record_health_check

ServiceStatus = Literal["ok", "degraded", "down"]


@dataclass(frozen=True)
class ServiceHealth:
    id: str
    status: ServiceStatus
    latency_ms: int
    detail: str = ""


@dataclass(frozen=True)
class PlatformStatus:
    checked_at: str
    server_time: str
    timezone: str
    overall_status: ServiceStatus
    services: list[ServiceHealth]

    def as_response(self) -> dict:
        return {
            "checked_at": self.checked_at,
            "server_time": self.server_time,
            "timezone": self.timezone,
            "overall_status": self.overall_status,
            "services": [asdict(service) for service in self.services],
        }


def _check_database() -> ServiceHealth:
    started = time.perf_counter()
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
        latency_ms = int((time.perf_counter() - started) * 1000)
        return ServiceHealth(id="database", status="ok", latency_ms=latency_ms)
    except Exception as exc:  # noqa: BLE001
        latency_ms = int((time.perf_counter() - started) * 1000)
        return ServiceHealth(
            id="database",
            status="down",
            latency_ms=latency_ms,
            detail=str(exc),
        )


def _check_broker() -> ServiceHealth:
    started = time.perf_counter()
    connection = None
    try:
        from kombu import Connection

        connection = Connection(settings.CELERY_BROKER_URL)
        connection.connect()
        latency_ms = int((time.perf_counter() - started) * 1000)
        return ServiceHealth(id="broker", status="ok", latency_ms=latency_ms)
    except Exception as exc:  # noqa: BLE001
        latency_ms = int((time.perf_counter() - started) * 1000)
        return ServiceHealth(
            id="broker",
            status="down",
            latency_ms=latency_ms,
            detail=str(exc),
        )
    finally:
        if connection is not None:
            with suppress(Exception):
                connection.release()


def _check_workers() -> ServiceHealth:
    started = time.perf_counter()
    try:
        from cadence.celery import app

        inspect = app.control.inspect(timeout=1.0)
        ping = inspect.ping() if inspect else None
        latency_ms = int((time.perf_counter() - started) * 1000)
        if not ping:
            return ServiceHealth(
                id="worker",
                status="down",
                latency_ms=latency_ms,
                detail="No workers responded",
            )
        worker_count = len(ping)
        status: ServiceStatus = "ok" if worker_count > 0 else "down"
        detail = f"{worker_count} worker{'s' if worker_count != 1 else ''}"
        return ServiceHealth(
            id="worker",
            status=status,
            latency_ms=latency_ms,
            detail=detail,
        )
    except Exception as exc:  # noqa: BLE001
        latency_ms = int((time.perf_counter() - started) * 1000)
        return ServiceHealth(
            id="worker",
            status="down",
            latency_ms=latency_ms,
            detail=str(exc),
        )


def _overall_status(services: list[ServiceHealth]) -> ServiceStatus:
    if any(service.status == "down" for service in services):
        if all(service.status == "down" for service in services):
            return "down"
        return "degraded"
    if any(service.status == "degraded" for service in services):
        return "degraded"
    return "ok"


def collect_platform_status(*, project_timezone: str) -> PlatformStatus:
    now = dj_timezone.now()
    localized = now.astimezone(ZoneInfo(project_timezone))

    services = [
        ServiceHealth(id="api", status="ok", latency_ms=0),
        _check_database(),
        _check_broker(),
        _check_workers(),
    ]

    for service in services:
        record_health_check(
            service.id,
            status=service.status,
            latency_ms=service.latency_ms,
            detail=service.detail,
        )

    return PlatformStatus(
        checked_at=now.isoformat(),
        server_time=localized.isoformat(),
        timezone=project_timezone,
        overall_status=_overall_status(services),
        services=services,
    )
