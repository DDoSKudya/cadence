from django.db.models import QuerySet

from apps.notifications.models import NotificationJob


def list_notifications(
    *,
    status: str | None = None,
    task_id: int | None = None,
) -> QuerySet[NotificationJob]:
    queryset = NotificationJob.objects.select_related("task").order_by("-created_at")
    if status:
        queryset = queryset.filter(status=status)
    if task_id is not None:
        queryset = queryset.filter(task_id=task_id)
    return queryset
