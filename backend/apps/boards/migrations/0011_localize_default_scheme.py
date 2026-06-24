from django.db import migrations

DEFAULT_SCHEME_SLUG = "default"

SCHEME_NAMES = {
    "en": {
        "name": "Default",
        "description": "Backlog → In progress → Ready",
    },
    "ru": {
        "name": "Стандартная",
        "description": "Бэклог → В работе → Готово",
    },
}

COLUMN_NAMES = {
    "en": {
        "backlog": "Backlog",
        "in_progress": "In progress",
        "ready": "Ready",
    },
    "ru": {
        "backlog": "Бэклог",
        "in_progress": "В работе",
        "ready": "Готово",
    },
}


def _resolve_locale(project_settings_model):
    settings = project_settings_model.objects.first()
    language = getattr(settings, "language", "en") if settings else "en"
    if language not in SCHEME_NAMES:
        return "en"
    return language


def localize_default_scheme(apps, schema_editor):
    project_settings_model = apps.get_model("core", "ProjectSettings")
    board_scheme_model = apps.get_model("boards", "BoardScheme")
    board_scheme_column_model = apps.get_model("boards", "BoardSchemeColumn")
    board_column_model = apps.get_model("boards", "BoardColumn")

    locale = _resolve_locale(project_settings_model)
    scheme_labels = SCHEME_NAMES[locale]
    column_labels = COLUMN_NAMES[locale]

    board_scheme_model.objects.filter(slug=DEFAULT_SCHEME_SLUG).update(
        name=scheme_labels["name"],
        description=scheme_labels["description"],
    )

    scheme = board_scheme_model.objects.filter(slug=DEFAULT_SCHEME_SLUG).first()
    if scheme is None:
        return

    for system_type, name in column_labels.items():
        board_scheme_column_model.objects.filter(
            scheme=scheme,
            system_type=system_type,
        ).update(name=name)
        board_column_model.objects.filter(
            is_locked=True,
            system_type=system_type,
        ).update(name=name)


def restore_default_scheme_english(apps, schema_editor):
    board_scheme_model = apps.get_model("boards", "BoardScheme")
    board_scheme_column_model = apps.get_model("boards", "BoardSchemeColumn")
    board_column_model = apps.get_model("boards", "BoardColumn")

    scheme_labels = SCHEME_NAMES["en"]
    column_labels = COLUMN_NAMES["en"]

    board_scheme_model.objects.filter(slug=DEFAULT_SCHEME_SLUG).update(
        name=scheme_labels["name"],
        description=scheme_labels["description"],
    )

    scheme = board_scheme_model.objects.filter(slug=DEFAULT_SCHEME_SLUG).first()
    if scheme is None:
        return

    for system_type, name in column_labels.items():
        board_scheme_column_model.objects.filter(
            scheme=scheme,
            system_type=system_type,
        ).update(name=name)
        board_column_model.objects.filter(
            is_locked=True,
            system_type=system_type,
        ).update(name=name)


class Migration(migrations.Migration):
    dependencies = [
        ("boards", "0010_scheme_column_flex"),
        ("core", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(localize_default_scheme, restore_default_scheme_english),
    ]
