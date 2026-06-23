import pytest
from django.urls import reverse

from apps.analytics.exporters import export_report
from apps.analytics.filters import parse_filters_payload, period_bounds, resolve_tag_ids
from apps.analytics.models import (
    AnalyticsExportJob,
    ExportStatus,
    ExportType,
    FileFormat,
)
from apps.analytics.services import AnalyticsExportService
from apps.core.models import Tag
from conftest import close_task_via_api, create_task_via_api


@pytest.fixture
def analytics_task_data(api_client, planned_column, week_key):
    tag = Tag.objects.create(name="Analytics", slug="analytics")
    created = create_task_via_api(
        api_client,
        title="Analytics task",
        column_id=planned_column.id,
        week=week_key,
        tags=[tag.slug],
    )
    close_task_via_api(api_client, created.json()["id"])
    return {"task_id": created.json()["id"], "tag_slug": tag.slug}


@pytest.mark.django_db
@pytest.mark.parametrize(
    "endpoint_name",
    [
        pytest.param("analytics-summary", id="ec_analytics_summary_endpoint"),
        pytest.param("analytics-weekly-trend", id="ec_analytics_weekly_trend_endpoint"),
        pytest.param("analytics-breakdown", id="ec_analytics_breakdown_endpoint"),
        pytest.param("analytics-cycle-time", id="ec_analytics_cycle_time_endpoint"),
        pytest.param(
            "analytics-notifications", id="ec_analytics_notifications_endpoint"
        ),
        pytest.param("analytics-task-flow", id="ec_analytics_task_flow_endpoint"),
        pytest.param("analytics-archive", id="ec_analytics_archive_endpoint"),
    ],
)
def test_analytics_ec_all_api_endpoints_return_200(
    api_client, analytics_task_data, endpoint_name
):
    params = {}
    if endpoint_name == "analytics-breakdown":
        params["group_by"] = "tag"
    response = api_client.get(reverse(endpoint_name), params)
    assert response.status_code == 200


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("group_by", "expected"),
    [
        pytest.param("column", "column", id="ec_breakdown_by_column_valid"),
        pytest.param("tag", "tag", id="ec_breakdown_by_tag_valid"),
        pytest.param("source", "source", id="ec_breakdown_by_source_valid"),
        pytest.param("unknown", "unknown", id="ec_breakdown_unknown_returns_empty"),
    ],
)
def test_analytics_ec_breakdown_group_classes(
    api_client, analytics_task_data, group_by, expected
):
    response = api_client.get(reverse("analytics-breakdown"), {"group_by": group_by})
    assert response.status_code == 200
    assert response.json()["group_by"] == expected


@pytest.mark.django_db
def test_analytics_ec_filters_parse_filters_payload_period_bounds_and_tag_resolution(
    current_week,
):
    tag = Tag.objects.create(name="Ops", slug="ops")
    filters = parse_filters_payload(
        {
            "week": f"{current_week.iso_year}-W{current_week.iso_week:02d}",
            "from": current_week.starts_on.isoformat(),
            "to": current_week.ends_on.isoformat(),
            "tags": ["ops", "missing"],
            "source": "api",
        }
    )
    start, end = period_bounds(filters)
    assert start is not None
    assert end is not None
    assert filters.source == "api"
    ids = resolve_tag_ids(["ops", "OPS", "missing"])
    assert tag.id in ids


@pytest.mark.django_db
@pytest.mark.parametrize(
    "export_type",
    [
        pytest.param(ExportType.TASKS, id="ec_export_tasks_csv"),
        pytest.param(ExportType.ARCHIVE, id="ec_export_archive_csv"),
        pytest.param(ExportType.WEEKLY_SUMMARY, id="ec_export_weekly_summary_csv"),
        pytest.param(ExportType.TAG_SUMMARY, id="ec_export_tag_summary_csv"),
        pytest.param(ExportType.NOTIFICATION_REPORT, id="ec_export_notifications_csv"),
        pytest.param(ExportType.JOBS_REPORT, id="ec_export_jobs_csv"),
        pytest.param(ExportType.IMPORTS_REPORT, id="ec_export_imports_csv"),
    ],
)
def test_analytics_ec_export_all_types_csv(
    media_root, analytics_task_data, export_type
):
    export_job = AnalyticsExportJob.objects.create(
        export_type=export_type,
        file_format=FileFormat.CSV,
        status=ExportStatus.PENDING,
        filters={},
    )
    relative_path, rows = export_report(export_job)
    assert str(relative_path).endswith(".csv")
    assert rows >= 0


@pytest.mark.django_db
def test_analytics_ec_export_weekly_summary_xlsx(media_root, analytics_task_data):
    export_job = AnalyticsExportJob.objects.create(
        export_type=ExportType.WEEKLY_SUMMARY,
        file_format=FileFormat.XLSX,
        status=ExportStatus.PENDING,
        filters={},
    )
    relative_path, rows = export_report(export_job)
    assert str(relative_path).endswith(".xlsx")
    assert rows >= 0


@pytest.mark.django_db
def test_analytics_ec_export_service_invalid_type_rejected():
    with pytest.raises(ValueError):
        AnalyticsExportService.create(
            export_type="invalid", file_format=FileFormat.CSV, filters={}
        )


@pytest.mark.django_db
def test_analytics_ec_export_download_not_ready_returns_409(api_client):
    export_job = AnalyticsExportJob.objects.create(
        export_type=ExportType.TASKS,
        file_format=FileFormat.CSV,
        status=ExportStatus.PENDING,
        filters={},
    )
    response = api_client.get(
        reverse("analytics-export-download", args=[export_job.id])
    )
    assert response.status_code == 409
