from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("boards", "0011_localize_default_scheme"),
    ]

    operations = [
        migrations.CreateModel(
            name="StatusTransition",
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
                (
                    "from_status",
                    models.CharField(
                        choices=[
                            ("backlog", "Backlog"),
                            ("planned", "Planned"),
                            ("in_progress", "In Progress"),
                            ("blocked", "Blocked"),
                            ("review", "Review"),
                            ("ready", "Ready"),
                            ("done", "Done"),
                        ],
                        max_length=20,
                    ),
                ),
                (
                    "to_status",
                    models.CharField(
                        choices=[
                            ("backlog", "Backlog"),
                            ("planned", "Planned"),
                            ("in_progress", "In Progress"),
                            ("blocked", "Blocked"),
                            ("review", "Review"),
                            ("ready", "Ready"),
                            ("done", "Done"),
                        ],
                        max_length=20,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "board",
                    models.ForeignKey(
                        on_delete=models.deletion.CASCADE,
                        related_name="status_transitions",
                        to="boards.board",
                    ),
                ),
            ],
        ),
        migrations.AddConstraint(
            model_name="statustransition",
            constraint=models.UniqueConstraint(
                fields=("board", "from_status", "to_status"),
                name="uq_status_transition_pair",
            ),
        ),
        migrations.AddConstraint(
            model_name="statustransition",
            constraint=models.CheckConstraint(
                condition=models.Q(
                    ("from_status", models.F("to_status")),
                    _negated=True,
                ),
                name="chk_status_transition_distinct",
            ),
        ),
        migrations.AddIndex(
            model_name="statustransition",
            index=models.Index(
                fields=["board", "from_status"],
                name="idx_status_trans_board_from",
            ),
        ),
    ]
