from django.urls import path

from apps.weeks.views import CurrentWeekView

urlpatterns = [
    path("weeks/current/", CurrentWeekView.as_view(), name="week-current"),
]
