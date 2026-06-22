from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0004_notification_settings"),
    ]

    operations = [
        migrations.AddField(
            model_name="projectsettings",
            name="telegram_bot_check_ok",
            field=models.BooleanField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="projectsettings",
            name="telegram_bot_check_message",
            field=models.CharField(blank=True, default="", max_length=255),
        ),
        migrations.AddField(
            model_name="projectsettings",
            name="telegram_bot_checked_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
