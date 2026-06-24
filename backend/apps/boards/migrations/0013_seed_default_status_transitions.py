from django.db import migrations

DEFAULT_STATUS_TRANSITIONS = (
    ("backlog", "in_progress"),
    ("in_progress", "ready"),
)


def seed_default_status_transitions(apps, schema_editor):
    board_model = apps.get_model("boards", "Board")
    scheme_model = apps.get_model("boards", "BoardScheme")
    status_transition_model = apps.get_model("boards", "StatusTransition")

    board = board_model.objects.filter(slug="main").first()
    if board is None:
        return

    default_scheme = scheme_model.objects.filter(slug="default").first()
    if default_scheme is None or board.active_scheme_id != default_scheme.id:
        return

    if status_transition_model.objects.filter(board=board).exists():
        return

    status_transition_model.objects.bulk_create(
        [
            status_transition_model(
                board=board,
                from_status=from_status,
                to_status=to_status,
            )
            for from_status, to_status in DEFAULT_STATUS_TRANSITIONS
        ],
    )


def clear_default_status_transitions(apps, schema_editor):
    board_model = apps.get_model("boards", "Board")
    status_transition_model = apps.get_model("boards", "StatusTransition")

    board = board_model.objects.filter(slug="main").first()
    if board is None:
        return

    status_transition_model.objects.filter(board=board).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("boards", "0012_status_transition"),
    ]

    operations = [
        migrations.RunPython(
            seed_default_status_transitions,
            clear_default_status_transitions,
        ),
    ]
