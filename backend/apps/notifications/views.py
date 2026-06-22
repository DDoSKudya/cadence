from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.notifications.reminders import TaskReminderService
from apps.notifications.selectors import list_notifications
from apps.notifications.serializers import NotificationJobSerializer
from apps.tasks.selectors import get_board_task


class NotificationListView(APIView):
    def get(self, request):
        queryset = list_notifications(
            status=request.query_params.get("status") or None,
            task_id=request.query_params.get("task_id") or None,
        )
        return Response(NotificationJobSerializer(queryset[:100], many=True).data)


class TaskNotifyView(APIView):
    def post(self, request, pk: int):
        task = get_board_task(pk)
        notification = TaskReminderService.notify(task)
        if notification is None:
            return Response(
                {"detail": "Telegram notifications are disabled or not configured."},
                status=400,
            )
        return Response(NotificationJobSerializer(notification).data, status=201)


class TaskReminderSnoozeView(APIView):
    def post(self, request, pk: int):
        task = get_board_task(pk)
        minutes = request.data.get("minutes")
        parsed_minutes = None
        if minutes is not None:
            try:
                parsed_minutes = int(minutes)
            except (TypeError, ValueError) as exc:
                raise ValidationError({"minutes": "Must be an integer."}) from exc
            if parsed_minutes < 1:
                raise ValidationError({"minutes": "Must be at least 1."})

        from apps.tasks.serializers import TaskSerializer

        updated = TaskReminderService.snooze(
            task,
            request=request,
            minutes=parsed_minutes,
        )
        return Response(TaskSerializer(updated).data)


class TaskReminderCancelView(APIView):
    def post(self, request, pk: int):
        from apps.tasks.serializers import TaskSerializer

        task = get_board_task(pk)
        updated = TaskReminderService.cancel(task, request=request)
        return Response(TaskSerializer(updated).data)
