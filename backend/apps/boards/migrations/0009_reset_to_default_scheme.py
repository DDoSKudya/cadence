from django.db import migrations


def reset_to_default_scheme(apps, schema_editor):
    board_model = apps.get_model("boards", "Board")
    board_column_model = apps.get_model("boards", "BoardColumn")
    board_scheme_model = apps.get_model("boards", "BoardScheme")
    board_scheme_column_model = apps.get_model("boards", "BoardSchemeColumn")
    column_transition_model = apps.get_model("boards", "ColumnTransition")
    task_model = apps.get_model("tasks", "Task")

    task_model.objects.all().delete()

    scheme, _created = board_scheme_model.objects.get_or_create(
        slug="default",
        defaults={
            "name": "Default",
            "description": "Backlog → Work in progress → Ready",
            "is_locked": True,
        },
    )

    template_columns = (
        {
            "position": 0,
            "name": "Backlog",
            "system_type": "backlog",
            "color": "slate",
        },
        {
            "position": 1,
            "name": "Work in progress",
            "system_type": "in_progress",
            "color": "amber",
        },
        {
            "position": 2,
            "name": "Ready",
            "system_type": "ready",
            "color": "green",
        },
    )
    for column in template_columns:
        board_scheme_column_model.objects.update_or_create(
            scheme=scheme,
            system_type=column["system_type"],
            defaults={
                "name": column["name"],
                "color": column["color"],
                "position": column["position"],
            },
        )

    board = board_model.objects.filter(slug="main").first()
    if board is None:
        return

    column_transition_model.objects.filter(board=board).delete()
    board_column_model.objects.filter(board=board).delete()

    columns_by_type: dict[str, object] = {}
    for template in board_scheme_column_model.objects.filter(scheme=scheme).order_by(
        "position",
    ):
        column = board_column_model.objects.create(
            board=board,
            name=template.name,
            system_type=template.system_type,
            color=template.color,
            position=template.position,
            is_locked=True,
        )
        columns_by_type[column.system_type] = column

    board.active_scheme = scheme
    board.save(update_fields=["active_scheme"])

    transitions = (
        ("backlog", "in_progress"),
        ("in_progress", "ready"),
    )
    for from_type, to_type in transitions:
        from_column = columns_by_type.get(from_type)
        to_column = columns_by_type.get(to_type)
        if from_column is None or to_column is None:
            continue
        column_transition_model.objects.create(
            board=board,
            from_column=from_column,
            to_column=to_column,
        )


class Migration(migrations.Migration):
    dependencies = [
        ("boards", "0008_board_scheme"),
        ("tasks", "0003_alter_task_options_alter_taskevent_options"),
    ]

    operations = [
        migrations.RunPython(reset_to_default_scheme, migrations.RunPython.noop),
    ]
