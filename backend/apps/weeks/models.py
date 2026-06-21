from django.db import models


class Week(models.Model):
    id: int

    iso_year = models.PositiveIntegerField()
    iso_week = models.PositiveIntegerField()
    starts_on = models.DateField()
    ends_on = models.DateField()
    review_notes = models.TextField(blank=True, default="")
    closed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-iso_year", "-iso_week")
        constraints = (
            models.UniqueConstraint(
                fields=["iso_year", "iso_week"],
                name="uq_weeks_iso_year_week",
            ),
            models.CheckConstraint(
                condition=models.Q(iso_week__gte=1, iso_week__lte=53),
                name="chk_weeks_iso_week",
            ),
            models.CheckConstraint(
                condition=models.Q(starts_on__lte=models.F("ends_on")),
                name="chk_weeks_range",
            ),
        )
        indexes = (models.Index(fields=["closed_at"], name="idx_weeks_closed_at"),)

    def __str__(self) -> str:
        return f"{self.iso_year}-W{self.iso_week:02d}"
