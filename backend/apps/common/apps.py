import logging
from logging.handlers import RotatingFileHandler

from django.apps import AppConfig

from apps.common.request_id import RequestIdFilter


class CommonConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.common"

    def ready(self) -> None:
        from apps.common import celery_logging  # noqa: F401

        self._configure_service_logging()

    def _configure_service_logging(self) -> None:
        from apps.common.log_handlers import ServiceLogHandler
        from apps.common.service_logs import log_dir
        from cadence.settings.environment import env

        service_name = env.str("CADENCE_SERVICE_NAME", default="api")
        formatter = logging.Formatter(
            "[%(asctime)s] %(levelname)s %(name)s %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        request_filter = RequestIdFilter()
        log_path = log_dir()

        def attach_handlers(logger: logging.Logger) -> None:
            has_handler = any(
                isinstance(handler, ServiceLogHandler) for handler in logger.handlers
            )
            if has_handler:
                return

            buffer_handler = ServiceLogHandler(service_name=service_name)
            buffer_handler.setFormatter(formatter)
            buffer_handler.addFilter(request_filter)
            logger.addHandler(buffer_handler)

            try:
                log_path.mkdir(parents=True, exist_ok=True)
                log_file = log_path / f"{service_name}.log"
                file_handler = RotatingFileHandler(
                    log_file,
                    maxBytes=2_000_000,
                    backupCount=3,
                    encoding="utf-8",
                )
            except OSError:
                return

            file_handler.setFormatter(formatter)
            file_handler.addFilter(request_filter)
            logger.addHandler(file_handler)

        attach_handlers(logging.getLogger())
        attach_handlers(logging.getLogger("cadence"))
