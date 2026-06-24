import django.db.models.deletion
from django.db import migrations, models


def seed_default_scheme_transitions(apps, schema_editor):
    board_scheme_model = apps.get_model("boards", "BoardScheme")
    scheme_transition_model = apps.get_model("boards", "BoardSchemeTransition")

    scheme = board_scheme_model.objects.filter(slug="default").first()
    if scheme is None:
        return

    scheme_transition_model.objects.bulk_create(
        [
            scheme_transition_model(
                scheme=scheme,
                from_position=0,
                to_position=1,
            ),
            scheme_transition_model(
                scheme=scheme,
                from_position=1,
                to_position=2,
            ),
        ],
        ignore_conflicts=True,
    )


def migrate_active_board_transitions_to_schemes(apps, schema_editor):
    board_model = apps.get_model("boards", "Board")
    board_column_model = apps.get_model("boards", "BoardColumn")
    column_transition_model = apps.get_model("boards", "ColumnTransition")
    scheme_transition_model = apps.get_model("boards", "BoardSchemeTransition")

    for board in board_model.objects.filter(
        active_scheme__isnull=False,
        active_scheme__is_locked=False,
    ).select_related("active_scheme"):
        scheme = board.active_scheme
        if scheme_transition_model.objects.filter(scheme=scheme).exists():
            continue

        positions = {
            column.id: column.position
            for column in board_column_model.objects.filter(
                board=board,
                is_active=True,
            )
        }
        pairs: set[tuple[int, int]] = set()
        for transition in column_transition_model.objects.filter(board=board):
            from_position = positions.get(transition.from_column_id)
            to_position = positions.get(transition.to_column_id)
            if (
                from_position is None
                or to_position is None
                or from_position == to_position
            ):
                continue
            pairs.add((from_position, to_position))

        if not pairs:
            continue

        scheme_transition_model.objects.bulk_create(
            [
                scheme_transition_model(
                    scheme=scheme,
                    from_position=from_position,
                    to_position=to_position,
                )
                for from_position, to_position in sorted(pairs)
            ],
            ignore_conflicts=True,
        )


class Migration(migrations.Migration):
    dependencies = [
        ("boards", "0019_task_status_on_flow"),
    ]

    operations = [
        migrations.CreateModel(
            name="BoardSchemeTransition",
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
                ("from_position", models.PositiveIntegerField()),
                ("to_position", models.PositiveIntegerField()),
                (
                    "scheme",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="transitions",
                        to="boards.boardscheme",
                    ),
                ),
            ],
            options={
                "ordering": ("from_position", "to_position"),
            },
        ),
        migrations.AddConstraint(
            model_name="boardschemetransition",
            constraint=models.UniqueConstraint(
                fields=("scheme", "from_position", "to_position"),
                name="uq_board_scheme_transition_pair",
            ),
        ),
        migrations.AddConstraint(
            model_name="boardschemetransition",
            constraint=models.CheckConstraint(
                condition=models.Q(
                    ("from_position", models.F("to_position")),
                    _negated=True,
                ),
                name="chk_board_scheme_transition_distinct",
            ),
        ),
        migrations.RunPython(
            seed_default_scheme_transitions,
            migrations.RunPython.noop,
        ),
        migrations.RunPython(
            migrate_active_board_transitions_to_schemes,
            migrations.RunPython.noop,
        ),
    ]
