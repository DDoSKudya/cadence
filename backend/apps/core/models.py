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
    telegram_bot_token = models.CharField(max_length=255, blank=True, default="")
    telegram_bot_username = models.CharField(max_length=80, blank=True, default="")
    telegram_recipients = models.JSONField(default=list, blank=True)
    telegram_bot_check_ok = models.BooleanField(null=True, blank=True)
    telegram_bot_check_message = models.CharField(
        max_length=255, blank=True, default=""
    )
    telegram_bot_checked_at = models.DateTimeField(null=True, blank=True)
    default_reminder_interval_minutes = models.PositiveIntegerField(default=1440)
    stale_in_progress_minutes = models.PositiveIntegerField(default=4320)
    stale_planned_minutes = models.PositiveIntegerField(default=10080)
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

    def telegram_recipient_chat_ids(self) -> list[str]:
        recipients = self.telegram_recipients or []
        chat_ids: list[str] = []
        for item in recipients:
            if not isinstance(item, dict):
                continue
            chat_id = str(item.get("chat_id", "")).strip()
            if chat_id:
                chat_ids.append(chat_id)
        return chat_ids

    def resolve_telegram_bot_token(self) -> str:
        if self.telegram_bot_token:
            return self.telegram_bot_token
        return settings.TELEGRAM_BOT_TOKEN


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
