from django.urls import path

from apps.jobs.views import JobCancelView, JobDetailView, JobListView, JobRetryView

urlpatterns = [
    path("jobs/", JobListView.as_view(), name="job-list"),
    path("jobs/<int:pk>/", JobDetailView.as_view(), name="job-detail"),
    path("jobs/<int:pk>/retry/", JobRetryView.as_view(), name="job-retry"),
    path("jobs/<int:pk>/cancel/", JobCancelView.as_view(), name="job-cancel"),
]
