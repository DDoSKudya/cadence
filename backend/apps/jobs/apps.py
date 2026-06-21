from django.apps import AppConfig


class JobsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.jobs"
    label = "jobs"

    def ready(self) -> None:
        from apps.imports import job_handlers as _import_job_handlers

        _import_job_handlers.register()
