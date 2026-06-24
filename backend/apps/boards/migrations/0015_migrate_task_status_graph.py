from django.db import migrations

STATUS_LAYOUT = {
    "backlog": (0, 0),
    "planned": (140, 100),
    "in_progress": (280, 0),
    "blocked": (420, 100),
    "review": (560, 100),
    "ready": (560, 0),
    "done": (700, 0),
}


def migrate_task_status_graph(apps, schema_editor):
    board_model = apps.get_model("boards", "Board")
    column_model = apps.get_model("boards", "BoardColumn")
    old_transition_model = apps.get_model("boards", "StatusTransition")
    task_status_model = apps.get_model("boards", "TaskStatus")
    task_status_transition_model = apps.get_model("boards", "TaskStatusTransition")
    task_model = apps.get_model("tasks", "Task")

    for board in board_model.objects.all():
        needed_types: set[str] = set()
        active_columns = list(
            column_model.objects.filter(board=board, is_active=True).order_by(
                "position",
            ),
        )
        for column in active_columns:
            needed_types.add(column.system_type)
        for transition in old_transition_model.objects.filter(board=board):
            needed_types.add(transition.from_status)
            needed_types.add(transition.to_status)

        if not needed_types:
            continue

        columns_by_type = {column.system_type: column for column in active_columns}
        statuses_by_slug: dict[str, object] = {}
        for index, slug in enumerate(sorted(needed_types)):
            column = columns_by_type.get(slug)
            layout_x, layout_y = STATUS_LAYOUT.get(slug, (index * 200, 120))
            fallback_name = slug.replace("_", " ").title()
            status = task_status_model.objects.create(
                board=board,
                name=column.name if column is not None else fallback_name,
                slug=slug,
                color=column.color if column is not None else "slate",
                layout_x=layout_x,
                layout_y=layout_y,
                position=index,
                is_initial=slug == "backlog",
            )
            statuses_by_slug[slug] = status

        for transition in old_transition_model.objects.filter(board=board):
            from_status = statuses_by_slug.get(transition.from_status)
            to_status = statuses_by_slug.get(transition.to_status)
            if from_status is None or to_status is None:
                continue
            task_status_transition_model.objects.create(
                board=board,
                from_status=from_status,
                to_status=to_status,
            )

        for column in active_columns:
            status = statuses_by_slug.get(column.system_type)
            if status is None:
                continue
            column.task_status_id = status.id
            column.save(update_fields=["task_status_id"])

        for task in task_model.objects.filter(board=board).select_related("column"):
            if task.column_id is None:
                continue
            status = statuses_by_slug.get(task.column.system_type)
            if status is None:
                continue
            task.task_status_id = status.id
            task.save(update_fields=["task_status_id"])


def reverse_migrate_task_status_graph(apps, schema_editor):
    board_model = apps.get_model("boards", "Board")
    column_model = apps.get_model("boards", "BoardColumn")
    old_transition_model = apps.get_model("boards", "StatusTransition")
    task_status_model = apps.get_model("boards", "TaskStatus")
    task_status_transition_model = apps.get_model("boards", "TaskStatusTransition")
    task_model = apps.get_model("tasks", "Task")

    for board in board_model.objects.all():
        transitions = []
        for transition in task_status_transition_model.objects.filter(
            board=board,
        ).select_related(
            "from_status",
            "to_status",
        ):
            transitions.append(
                old_transition_model(
                    board=board,
                    from_status=transition.from_status.slug,
                    to_status=transition.to_status.slug,
                ),
            )
        if transitions:
            old_transition_model.objects.bulk_create(transitions)

        task_model.objects.filter(board=board).update(task_status_id=None)
        column_model.objects.filter(board=board).update(task_status_id=None)
        task_status_transition_model.objects.filter(board=board).delete()
        task_status_model.objects.filter(board=board).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("boards", "0014_task_status_models"),
        ("tasks", "0004_task_task_status"),
    ]

    operations = [
        migrations.RunPython(
            migrate_task_status_graph,
            reverse_migrate_task_status_graph,
        ),
        migrations.DeleteModel(
            name="StatusTransition",
        ),
    ]
