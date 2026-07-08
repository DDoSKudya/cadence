from django.contrib.auth.hashers import make_password
from django.db import migrations

DEFAULT_USERNAME = "admin"
DEFAULT_PASSWORD = "admin"


def seed_default_superuser(apps, schema_editor):
    user_model = apps.get_model("auth", "User")
    user_model.objects.get_or_create(
        username=DEFAULT_USERNAME,
        defaults={
            "password": make_password(DEFAULT_PASSWORD),
            "is_superuser": True,
            "is_staff": True,
            "is_active": True,
            "email": "",
        },
    )


def remove_default_superuser(apps, schema_editor):
    user_model = apps.get_model("auth", "User")
    user_model.objects.filter(username=DEFAULT_USERNAME).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0008_tag_scheme"),
        ("auth", "0012_alter_user_first_name_max_length"),
    ]

    operations = [
        migrations.RunPython(seed_default_superuser, remove_default_superuser),
    ]
