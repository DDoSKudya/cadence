from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("boards", "0018_widen_status_flow_layout"),
    ]

    operations = [
        migrations.AddField(
            model_name="taskstatus",
            name="on_flow",
            field=models.BooleanField(default=True),
        ),
    ]
