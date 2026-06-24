import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("boards", "0013_seed_default_status_transitions"),
    ]

    operations = [
        migrations.CreateModel(
            name="TaskStatus",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("name", models.CharField(max_length=100)),
                ("slug", models.SlugField(max_length=60)),
                ("color", models.CharField(default="slate", max_length=20)),
                ("layout_x", models.FloatField(default=0)),
                ("layout_y", models.FloatField(default=0)),
                ("position", models.PositiveIntegerField(default=0)),
                ("is_initial", models.BooleanField(default=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "board",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="task_statuses",
                        to="boards.board",
                    ),
                ),
            ],
            options={
                "ordering": ("position", "name"),
            },
        ),
        migrations.CreateModel(
            name="TaskStatusTransition",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "board",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="task_status_transitions",
                        to="boards.board",
                    ),
                ),
                (
                    "from_status",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="outgoing_transitions",
                        to="boards.taskstatus",
                    ),
                ),
                (
                    "to_status",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="incoming_transitions",
                        to="boards.taskstatus",
                    ),
                ),
            ],
        ),
        migrations.AddField(
            model_name="boardcolumn",
            name="task_status",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="columns",
                to="boards.taskstatus",
            ),
        ),
        migrations.AddConstraint(
            model_name="taskstatus",
            constraint=models.UniqueConstraint(
                fields=("board", "slug"),
                name="uq_task_status_board_slug",
            ),
        ),
        migrations.AddIndex(
            model_name="taskstatus",
            index=models.Index(
                fields=["board", "position"],
                name="idx_task_status_board_pos",
            ),
        ),
        migrations.AddConstraint(
            model_name="taskstatustransition",
            constraint=models.UniqueConstraint(
                fields=("from_status", "to_status"),
                name="uq_task_status_transition_pair",
            ),
        ),
        migrations.AddConstraint(
            model_name="taskstatustransition",
            constraint=models.CheckConstraint(
                condition=~models.Q(from_status=models.F("to_status")),
                name="chk_task_status_transition_distinct",
            ),
        ),
        migrations.AddIndex(
            model_name="taskstatustransition",
            index=models.Index(
                fields=["board", "from_status"],
                name="idx_task_stat_trans_board_from",
            ),
        ),
    ]
