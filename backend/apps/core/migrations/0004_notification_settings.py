from django.db import migrations, models


def migrate_chat_id_to_recipients(apps, schema_editor):
    ProjectSettings = apps.get_model("core", "ProjectSettings")
    settings = ProjectSettings.objects.filter(pk=1).first()
    if settings is None:
        return

    chat_id = getattr(settings, "telegram_default_chat_id", "")
    if chat_id and not settings.telegram_recipients:
        settings.telegram_recipients = [
            {
                "chat_id": chat_id,
                "label": "Основной",
                "kind": "user",
            },
        ]
        settings.save(update_fields=["telegram_recipients"])


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0003_alter_apikey_options_alter_tag_options_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="projectsettings",
            name="telegram_bot_token",
            field=models.CharField(blank=True, default="", max_length=255),
        ),
        migrations.AddField(
            model_name="projectsettings",
            name="telegram_bot_username",
            field=models.CharField(blank=True, default="", max_length=80),
        ),
        migrations.AddField(
            model_name="projectsettings",
            name="telegram_recipients",
            field=models.JSONField(blank=True, default=list),
        ),
        migrations.RunPython(migrate_chat_id_to_recipients, migrations.RunPython.noop),
        migrations.RemoveField(
            model_name="projectsettings",
            name="telegram_default_chat_id",
        ),
    ]
