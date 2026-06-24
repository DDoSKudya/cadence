from django.db import migrations

from apps.boards.task_status_services import (
    WORKFLOW_CANCEL_FROM,
    WORKFLOW_STATUS_LAYOUT,
    WORKFLOW_TRANSITIONS,
)
from apps.common.i18n import DEFAULT_LOCALE, t


def reseed_default_workflow_graph(apps, schema_editor):
    board_model = apps.get_model("boards", "Board")
    scheme_model = apps.get_model("boards", "BoardScheme")
    column_model = apps.get_model("boards", "BoardColumn")
    task_status_model = apps.get_model("boards", "TaskStatus")
    task_transition_model = apps.get_model("boards", "TaskStatusTransition")

    default_scheme = scheme_model.objects.filter(slug="default").first()
    if default_scheme is None:
        return

    for board in board_model.objects.filter(active_scheme_id=default_scheme.id):
        columns_by_type = {
            column.system_type: column
            for column in column_model.objects.filter(board=board, is_active=True)
        }
        if not columns_by_type:
            continue

        board_id = board.pk
        task_transition_model.objects.filter(board_id=board_id).delete()
        task_status_model.objects.filter(board_id=board_id).delete()

        statuses_by_slug = {}
        for index, (
            slug,
            label_key,
            color,
            x,
            y,
            is_initial,
            is_terminal,
            column_type,
            rules,
        ) in enumerate(WORKFLOW_STATUS_LAYOUT):
            column = columns_by_type.get(column_type)
            status = task_status_model.objects.create(
                board_id=board_id,
                name=t(label_key, locale=DEFAULT_LOCALE),
                slug=slug,
                color=color,
                layout_x=x,
                layout_y=y,
                position=index,
                is_initial=is_initial,
                is_terminal=is_terminal,
                rules=rules,
                column_id=column.pk if column is not None else None,
            )
            statuses_by_slug[slug] = status

        transitions = []
        for from_slug, to_slug, rules in WORKFLOW_TRANSITIONS:
            from_status = statuses_by_slug.get(from_slug)
            to_status = statuses_by_slug.get(to_slug)
            if from_status is None or to_status is None:
                continue
            transitions.append(
                task_transition_model(
                    board_id=board_id,
                    from_status=from_status,
                    to_status=to_status,
                    rules=rules,
                ),
            )

        cancel_status = statuses_by_slug.get("cancel")
        if cancel_status is not None:
            for from_slug in WORKFLOW_CANCEL_FROM:
                from_status = statuses_by_slug.get(from_slug)
                if from_status is None:
                    continue
                transitions.append(
                    task_transition_model(
                        board_id=board_id,
                        from_status=from_status,
                        to_status=cancel_status,
                        rules={"auto_move_column": True},
                    ),
                )

        if transitions:
            task_transition_model.objects.bulk_create(transitions)


def noop_reverse(apps, schema_editor):
    return None


class Migration(migrations.Migration):
    dependencies = [
        ("boards", "0016_task_status_rules"),
    ]

    operations = [
        migrations.RunPython(reseed_default_workflow_graph, noop_reverse),
    ]
