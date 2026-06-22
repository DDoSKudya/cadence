from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.weeks.models import Week
from apps.weeks.review_serializers import (
    WeekCloseSerializer,
    WeekOpenTaskSerializer,
    WeekReviewNotesSerializer,
)
from apps.weeks.serializers import WeekSerializer
from apps.weeks.services import WeekCloseService, WeekReviewService


class WeekListView(APIView):
    def get(self, request):
        weeks = Week.objects.all().order_by("-iso_year", "-iso_week")[:52]
        return Response(WeekSerializer(weeks, many=True).data)


class WeekReviewView(APIView):
    def get_object(self, pk: int) -> Week:
        return get_object_or_404(Week, pk=pk)

    def get(self, request, pk: int):
        week = self.get_object(pk)
        data = WeekReviewService.build(week)
        return Response(
            {
                "week": WeekSerializer(data["week"]).data,
                "stats": {
                    "tasks_total": data["tasks_total"],
                    "tasks_closed": data["tasks_closed"],
                    "tasks_open": data["tasks_open"],
                },
                "open_tasks": WeekOpenTaskSerializer(
                    data["open_tasks"],
                    many=True,
                ).data,
            },
        )

    def patch(self, request, pk: int):
        week = self.get_object(pk)
        serializer = WeekReviewNotesSerializer(week, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(WeekSerializer(week).data)


class WeekCloseView(APIView):
    def post(self, request, pk: int):
        week = get_object_or_404(Week, pk=pk)
        serializer = WeekCloseSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = WeekCloseService.close(
            week,
            carry_over=serializer.validated_data["carry_over"],
        )
        return Response(
            {
                "week": WeekSerializer(week).data,
                "result": result,
            },
            status=status.HTTP_200_OK,
        )
