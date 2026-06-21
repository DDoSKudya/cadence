from django.db import migrations

BOARD = {"name": "Main", "slug": "main", "is_default": True}

COLUMNS = [
    {"position": 0, "name": "Backlog", "system_type": "backlog", "color": "slate"},
    {"position": 1, "name": "Planned", "system_type": "planned", "color": "blue"},
    {
        "position": 2,
        "name": "In Progress",
        "system_type": "in_progress",
        "color": "amber",
    },
    {"position": 3, "name": "Done", "system_type": "done", "color": "green"},
]


def seed_board(apps, schema_editor):
    board_model = apps.get_model("boards", "Board")
    column_model = apps.get_model("boards", "BoardColumn")

    board, _created = board_model.objects.get_or_create(
        slug=BOARD["slug"],
        defaults=BOARD,
    )
    if not board.is_default:
        board.is_default = True
        board.save(update_fields=["is_default"])

    for column in COLUMNS:
        column_model.objects.get_or_create(
            board=board,
            system_type=column["system_type"],
            defaults=column,
        )


def remove_board(apps, schema_editor):
    board_model = apps.get_model("boards", "Board")
    board_model.objects.filter(slug=BOARD["slug"]).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("boards", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(seed_board, remove_board),
    ]
