from django.db import migrations


def add_process_to_done_transition(apps, schema_editor):
    board_scheme_model = apps.get_model("boards", "BoardScheme")
    scheme_transition_model = apps.get_model(
        "boards",
        "BoardSchemeTaskStatusTransition",
    )
    task_status_model = apps.get_model("boards", "TaskStatus")
    task_transition_model = apps.get_model("boards", "TaskStatusTransition")

    scheme = board_scheme_model.objects.filter(slug="default").first()
    if scheme is not None:
        scheme_transition_model.objects.get_or_create(
            scheme=scheme,
            from_status_slug="process",
            to_status_slug="done",
            defaults={"rules": {"auto_move_column": True}},
        )

    board_ids = task_status_model.objects.values_list("board_id", flat=True).distinct()
    for board_id in board_ids:
        statuses = {
            status.slug: status
            for status in task_status_model.objects.filter(board_id=board_id)
        }
        from_status = statuses.get("process")
        to_status = statuses.get("done")
        if from_status is None or to_status is None:
            continue
        task_transition_model.objects.get_or_create(
            board_id=board_id,
            from_status=from_status,
            to_status=to_status,
            defaults={"rules": {"auto_move_column": True}},
        )


class Migration(migrations.Migration):
    dependencies = [
        ("boards", "0022_alter_taskstatus_on_flow"),
    ]

    operations = [
        migrations.RunPython(add_process_to_done_transition, migrations.RunPython.noop),
    ]
