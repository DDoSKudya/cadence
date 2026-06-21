from django.contrib import admin

from apps.weeks.models import Week


@admin.register(Week)
class WeekAdmin(admin.ModelAdmin):
    list_display = ("iso_year", "iso_week", "starts_on", "ends_on", "closed_at")
    list_filter = ("iso_year",)
    ordering = ("-iso_year", "-iso_week")
