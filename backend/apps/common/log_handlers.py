from __future__ import annotations

import logging

from apps.common.service_logs import record_service_log


class ServiceLogHandler(logging.Handler):
    def __init__(self, *, service_name: str) -> None:
        super().__init__()
        self.service_name = service_name

    def emit(self, record: logging.LogRecord) -> None:
        try:
            message = self.format(record)
            record_service_log(
                self.service_name,
                record.levelname,
                message,
                source="process",
            )
        except Exception:  # noqa: BLE001
            self.handleError(record)
