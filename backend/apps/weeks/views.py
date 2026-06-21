from rest_framework.response import Response
from rest_framework.views import APIView

from apps.weeks.serializers import WeekSerializer
from apps.weeks.services import WeekService


class CurrentWeekView(APIView):
    def get(self, request):
        week = WeekService.get_or_create_current_week()
        return Response(WeekSerializer(week).data)
