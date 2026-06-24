import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("boards", "0015_migrate_task_status_graph"),
    ]

    operations = [
        migrations.AddField(
            model_name="taskstatus",
            name="is_terminal",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="taskstatus",
            name="rules",
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.AddField(
            model_name="taskstatus",
            name="column",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="bound_statuses",
                to="boards.boardcolumn",
            ),
        ),
        migrations.AddField(
            model_name="taskstatustransition",
            name="rules",
            field=models.JSONField(blank=True, default=dict),
        ),
    ]
