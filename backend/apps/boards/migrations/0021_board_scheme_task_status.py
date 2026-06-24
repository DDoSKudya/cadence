from typing import Any

import django.db.models.deletion
from django.db import migrations, models

DEFAULT_STATUS_LAYOUT: tuple[
    tuple[str, str, int, int, bool, bool, int, dict[str, Any]],
    ...,
] = (
    ("open", "slate", 60, 60, True, False, 0, {"creation_only": True}),
    ("ready_on_develop", "blue", 340, 60, False, False, 0, {}),
    ("process", "amber", 620, 60, False, False, 1, {"auto_move_column": True}),
    ("testing", "indigo", 900, 60, False, False, 1, {"auto_move_column": True}),
    ("done", "green", 1180, 60, False, True, 2, {"auto_move_column": True}),
    ("cancel", "red", 760, 300, False, False, 2, {"auto_move_column": True}),
)

DEFAULT_STATUS_TRANSITIONS: tuple[tuple[str, str, dict[str, Any]], ...] = (
    ("open", "ready_on_develop", {"required_fields": ["description"]}),
    ("ready_on_develop", "process", {"auto_move_column": True}),
    ("process", "testing", {}),
    ("testing", "done", {"auto_move_column": True}),
    ("testing", "process", {}),
    ("testing", "ready_on_develop", {}),
)

DEFAULT_CANCEL_FROM = ("open", "ready_on_develop", "process", "testing")


def seed_default_scheme_task_statuses(apps, schema_editor):
    board_scheme_model = apps.get_model("boards", "BoardScheme")
    status_model = apps.get_model("boards", "BoardSchemeTaskStatus")
    transition_model = apps.get_model("boards", "BoardSchemeTaskStatusTransition")

    scheme = board_scheme_model.objects.filter(slug="default").first()
    if scheme is None:
        return

    if status_model.objects.filter(scheme=scheme).exists():
        return

    labels = {
        "open": "Open",
        "ready_on_develop": "Ready on develop",
        "process": "In progress",
        "testing": "Testing",
        "done": "Done",
        "cancel": "Cancel",
    }

    status_model.objects.bulk_create(
        [
            status_model(
                scheme=scheme,
                slug=slug,
                name=labels.get(slug, slug),
                color=color,
                layout_x=layout_x,
                layout_y=layout_y,
                on_flow=True,
                position=index,
                is_initial=is_initial,
                is_terminal=is_terminal,
                column_position=column_position,
                rules=rules,
            )
            for index, (
                slug,
                color,
                layout_x,
                layout_y,
                is_initial,
                is_terminal,
                column_position,
                rules,
            ) in enumerate(DEFAULT_STATUS_LAYOUT)
        ],
        ignore_conflicts=True,
    )

    transitions = [
        transition_model(
            scheme=scheme,
            from_status_slug=from_slug,
            to_status_slug=to_slug,
            rules=rules,
        )
        for from_slug, to_slug, rules in DEFAULT_STATUS_TRANSITIONS
    ]
    for from_slug in DEFAULT_CANCEL_FROM:
        transitions.append(
            transition_model(
                scheme=scheme,
                from_status_slug=from_slug,
                to_status_slug="cancel",
                rules={"auto_move_column": True},
            ),
        )
    transition_model.objects.bulk_create(transitions, ignore_conflicts=True)


def migrate_active_board_status_graphs_to_schemes(apps, schema_editor):
    board_model = apps.get_model("boards", "Board")
    board_column_model = apps.get_model("boards", "BoardColumn")
    task_status_model = apps.get_model("boards", "TaskStatus")
    task_transition_model = apps.get_model("boards", "TaskStatusTransition")
    scheme_status_model = apps.get_model("boards", "BoardSchemeTaskStatus")
    scheme_transition_model = apps.get_model(
        "boards",
        "BoardSchemeTaskStatusTransition",
    )

    for board in board_model.objects.filter(
        active_scheme__isnull=False,
        active_scheme__is_locked=False,
    ).select_related("active_scheme"):
        scheme = board.active_scheme
        if scheme_status_model.objects.filter(scheme=scheme).exists():
            continue

        column_positions = {
            column.id: column.position
            for column in board_column_model.objects.filter(board=board, is_active=True)
        }
        statuses = list(
            task_status_model.objects.filter(board=board).order_by("position", "name"),
        )
        if not statuses:
            continue

        scheme_status_model.objects.bulk_create(
            [
                scheme_status_model(
                    scheme=scheme,
                    slug=status.slug,
                    name=status.name,
                    color=status.color,
                    layout_x=status.layout_x,
                    layout_y=status.layout_y,
                    on_flow=status.on_flow,
                    position=status.position,
                    is_initial=status.is_initial,
                    is_terminal=status.is_terminal,
                    column_position=column_positions.get(status.column_id)
                    if status.column_id
                    else None,
                    rules=status.rules or {},
                )
                for status in statuses
            ],
            ignore_conflicts=True,
        )

        slug_by_id = {status.id: status.slug for status in statuses}
        transition_models = []
        for transition in task_transition_model.objects.filter(board=board):
            from_slug = slug_by_id.get(transition.from_status_id)
            to_slug = slug_by_id.get(transition.to_status_id)
            if from_slug is None or to_slug is None:
                continue
            transition_models.append(
                scheme_transition_model(
                    scheme=scheme,
                    from_status_slug=from_slug,
                    to_status_slug=to_slug,
                    rules=transition.rules or {},
                ),
            )
        if transition_models:
            scheme_transition_model.objects.bulk_create(
                transition_models,
                ignore_conflicts=True,
            )


class Migration(migrations.Migration):
    dependencies = [
        ("boards", "0020_board_scheme_transition"),
    ]

    operations = [
        migrations.CreateModel(
            name="BoardSchemeTaskStatus",
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
                ("slug", models.SlugField(max_length=60)),
                ("name", models.CharField(max_length=100)),
                ("color", models.CharField(default="slate", max_length=20)),
                ("layout_x", models.FloatField(default=0)),
                ("layout_y", models.FloatField(default=0)),
                ("on_flow", models.BooleanField(default=False)),
                ("position", models.PositiveIntegerField(default=0)),
                ("is_initial", models.BooleanField(default=False)),
                ("is_terminal", models.BooleanField(default=False)),
                ("column_position", models.PositiveIntegerField(blank=True, null=True)),
                ("rules", models.JSONField(blank=True, default=dict)),
                (
                    "scheme",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="task_statuses",
                        to="boards.boardscheme",
                    ),
                ),
            ],
            options={
                "ordering": ("position", "name"),
            },
        ),
        migrations.CreateModel(
            name="BoardSchemeTaskStatusTransition",
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
                ("from_status_slug", models.SlugField(max_length=60)),
                ("to_status_slug", models.SlugField(max_length=60)),
                ("rules", models.JSONField(blank=True, default=dict)),
                (
                    "scheme",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="task_status_transitions",
                        to="boards.boardscheme",
                    ),
                ),
            ],
            options={
                "ordering": ("from_status_slug", "to_status_slug"),
            },
        ),
        migrations.AddConstraint(
            model_name="boardschemetaskstatus",
            constraint=models.UniqueConstraint(
                fields=("scheme", "slug"),
                name="uq_board_scheme_task_status_slug",
            ),
        ),
        migrations.AddConstraint(
            model_name="boardschemetaskstatustransition",
            constraint=models.UniqueConstraint(
                fields=("scheme", "from_status_slug", "to_status_slug"),
                name="uq_board_scheme_task_status_transition_pair",
            ),
        ),
        migrations.AddConstraint(
            model_name="boardschemetaskstatustransition",
            constraint=models.CheckConstraint(
                condition=models.Q(
                    ("from_status_slug", models.F("to_status_slug")),
                    _negated=True,
                ),
                name="chk_board_scheme_task_status_transition_distinct",
            ),
        ),
        migrations.RunPython(
            seed_default_scheme_task_statuses,
            migrations.RunPython.noop,
        ),
        migrations.RunPython(
            migrate_active_board_status_graphs_to_schemes,
            migrations.RunPython.noop,
        ),
    ]
