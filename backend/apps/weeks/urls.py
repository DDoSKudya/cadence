from django.urls import path

from apps.weeks.review_views import WeekCloseView, WeekListView, WeekReviewView
from apps.weeks.views import CurrentWeekView

urlpatterns = [
    path("weeks/current/", CurrentWeekView.as_view(), name="week-current"),
    path("weeks/", WeekListView.as_view(), name="week-list"),
    path("weeks/<int:pk>/review/", WeekReviewView.as_view(), name="week-review"),
    path("weeks/<int:pk>/close/", WeekCloseView.as_view(), name="week-close"),
]
