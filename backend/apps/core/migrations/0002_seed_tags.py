from django.db import migrations

TAGS = ["mentor", "course", "practice", "review", "backend", "frontend"]


def seed_tags(apps, schema_editor):
    tag_model = apps.get_model("core", "Tag")
    for name in TAGS:
        tag_model.objects.get_or_create(
            slug=name,
            defaults={"name": name, "color": "#64748b", "is_active": True},
        )


def remove_seed_tags(apps, schema_editor):
    tag_model = apps.get_model("core", "Tag")
    tag_model.objects.filter(slug__in=TAGS).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(seed_tags, remove_seed_tags),
    ]
