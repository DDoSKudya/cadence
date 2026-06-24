import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("boards", "0014_task_status_models"),
        ("tasks", "0003_alter_task_options_alter_taskevent_options"),
    ]

    operations = [
        migrations.AddField(
            model_name="task",
            name="task_status",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="tasks",
                to="boards.taskstatus",
            ),
        ),
    ]
