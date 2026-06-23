from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0005_telegram_bot_check"),
    ]

    operations = [
        migrations.AddField(
            model_name="projectsettings",
            name="language",
            field=models.CharField(
                choices=[("en", "English"), ("ru", "Russian")],
                default="en",
                max_length=2,
            ),
        ),
    ]
