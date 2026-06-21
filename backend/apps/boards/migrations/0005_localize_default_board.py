from django.db import migrations

DEFAULT_COLUMN_NAMES = {
    "backlog": "Бэклог",
    "planned": "План",
    "in_progress": "В работе",
    "done": "Готово",
}


def localize_default_board(apps, schema_editor):
    board_model = apps.get_model("boards", "Board")
    column_model = apps.get_model("boards", "BoardColumn")

    board_model.objects.filter(slug="main", name="Main").update(name="Главная")
    board = board_model.objects.filter(slug="main").first()
    if board is None:
        return

    for system_type, name in DEFAULT_COLUMN_NAMES.items():
        column_model.objects.filter(
            board=board,
            system_type=system_type,
        ).update(name=name)


def restore_default_board_names(apps, schema_editor):
    board_model = apps.get_model("boards", "Board")
    column_model = apps.get_model("boards", "BoardColumn")

    board_model.objects.filter(slug="main", name="Главная").update(name="Main")
    board = board_model.objects.filter(slug="main").first()
    if board is None:
        return

    previous_names = {
        "backlog": "Backlog",
        "planned": "Planned",
        "in_progress": "In Progress",
        "done": "Done",
    }
    for system_type, name in previous_names.items():
        column_model.objects.filter(
            board=board,
            system_type=system_type,
        ).update(name=name)


class Migration(migrations.Migration):
    dependencies = [
        ("boards", "0004_rename_boardcolumn_indexes"),
    ]

    operations = [
        migrations.RunPython(localize_default_board, restore_default_board_names),
    ]
