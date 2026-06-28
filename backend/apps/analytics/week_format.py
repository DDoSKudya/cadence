from __future__ import annotations

import re

_WEEK_KEY = re.compile(r"^(\d{4})-W(\d{2})$")


def format_week_label(week_key: str) -> str:
    match = _WEEK_KEY.match(str(week_key).strip())
    if match is None:
        return str(week_key)
    return f"{match.group(1)} · W{match.group(2)}"
