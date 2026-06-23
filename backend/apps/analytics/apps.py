from django.apps import AppConfig


class AnalyticsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.analytics"
    label = "analytics"

    def ready(self) -> None:
        from apps.analytics import job_handlers as _analytics_job_handlers

        _analytics_job_handlers.register()
