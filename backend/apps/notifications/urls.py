from django.urls import path

from apps.notifications.views import (
    NotificationListView,
    TaskNotifyView,
    TaskReminderCancelView,
    TaskReminderSnoozeView,
)

urlpatterns = [
    path("notifications/", NotificationListView.as_view(), name="notification-list"),
    path("tasks/<int:pk>/notify/", TaskNotifyView.as_view(), name="task-notify"),
    path(
        "tasks/<int:pk>/reminders/snooze/",
        TaskReminderSnoozeView.as_view(),
        name="task-reminder-snooze",
    ),
    path(
        "tasks/<int:pk>/reminders/cancel/",
        TaskReminderCancelView.as_view(),
        name="task-reminder-cancel",
    ),
]
