from __future__ import annotations

import re
from datetime import datetime

from django.utils import timezone

from apps.analytics.filters import AnalyticsFilters

_TOKEN_RE = re.compile(r"[^a-zA-Z0-9]+")


def _token(value: str, *, max_len: int = 32) -> str:
    cleaned = _TOKEN_RE.sub("-", str(value).strip().lower()).strip("-")
    if not cleaned:
        return "na"
    return cleaned[:max_len]


def _safe_export_type(export_type: str) -> str:
    cleaned = re.sub(r"[^a-z0-9_]+", "", export_type.strip().lower())
    return cleaned or "export"


def build_export_filename_stem(
    export_type: str,
    filters: AnalyticsFilters,
    *,
    generated_at: datetime | None = None,
) -> str:
    """ASCII export filename stem: report, period filters, generation timestamp."""
    parts: list[str] = [_safe_export_type(export_type)]

    if filters.week is not None:
        parts.append(f"{filters.week.iso_year}-W{filters.week.iso_week:02d}")
    elif filters.from_dt is not None or filters.to_dt is not None:
        if filters.from_dt is not None and filters.to_dt is not None:
            parts.append(
                f"{filters.from_dt.date().isoformat()}_to_{filters.to_dt.date().isoformat()}"
            )
        elif filters.from_dt is not None:
            parts.append(f"from_{filters.from_dt.date().isoformat()}")
        elif filters.to_dt is not None:
            parts.append(f"to_{filters.to_dt.date().isoformat()}")

    if filters.tags:
        tag_tokens = [_token(tag, max_len=24) for tag in filters.tags[:3]]
        tag_part = "-".join(tag_tokens)
        if len(filters.tags) > 3:
            tag_part = f"{tag_part}-more"
        parts.append(f"tags-{tag_part}")

    if filters.source:
        parts.append(f"source-{_token(filters.source, max_len=24)}")

    timestamp = timezone.localtime(generated_at or timezone.now()).strftime(
        "%Y-%m-%d_%H%M"
    )
    parts.append(timestamp)
    return "_".join(parts)
