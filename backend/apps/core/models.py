import secrets

from django.conf import settings
from django.contrib.auth.hashers import check_password, make_password
from django.db import models
from django.utils import timezone
from django.utils.text import slugify


class ApiKey(models.Model):
    id: int

    name = models.CharField(max_length=100)
    prefix = models.CharField(max_length=12, unique=True, editable=False)
    key_hash = models.CharField(max_length=128)
    is_active = models.BooleanField(default=True)
    last_used_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("name",)

    def __str__(self) -> str:
        return self.name

    @classmethod
    def issue(cls, name: str) -> tuple["ApiKey", str]:
        raw_key = f"cd_{secrets.token_urlsafe(32)}"
        api_key = cls.objects.create(
            name=name,
            prefix=raw_key[:12],
            key_hash=make_password(raw_key),
        )
        return api_key, raw_key

    @classmethod
    def verify(cls, raw_key: str) -> "ApiKey | None":
        if not raw_key:
            return None

        api_key = cls.objects.filter(prefix=raw_key[:12], is_active=True).first()
        if api_key is None or not check_password(raw_key, api_key.key_hash):
            return None

        api_key.last_used_at = timezone.now()
        api_key.save(update_fields=["last_used_at"])
        return api_key


class ProjectSettings(models.Model):
    id: int

    timezone = models.CharField(max_length=64, default=settings.TIME_ZONE)
    json_inbox_enabled = models.BooleanField(default=True)
    telegram_enabled = models.BooleanField(default=False)
    default_reminder_interval_minutes = models.PositiveIntegerField(default=1440)
    quiet_hours_start = models.TimeField(null=True, blank=True)
    quiet_hours_end = models.TimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Project settings"
        verbose_name_plural = "Project settings"

    def __str__(self) -> str:
        return "Project settings"

    @classmethod
    def load(cls) -> "ProjectSettings":
        settings_obj, _created = cls.objects.get_or_create(pk=1)
        return settings_obj

    def save(self, *args, **kwargs) -> None:
        self.pk = 1
        super().save(*args, **kwargs)


class Tag(models.Model):
    id: int

    name = models.CharField(max_length=50)
    slug = models.SlugField(max_length=60, unique=True, blank=True)
    color = models.CharField(max_length=20, blank=True, default="#64748b")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("name",)

    def __str__(self) -> str:
        return self.name

    def save(self, *args, **kwargs) -> None:
        if not self.slug:
            self.slug = slugify(self.name) or self.name.strip().lower()
        super().save(*args, **kwargs)
