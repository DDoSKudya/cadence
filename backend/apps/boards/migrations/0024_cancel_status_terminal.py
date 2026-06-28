from django.db import migrations


def mark_cancel_terminal(apps, schema_editor):
    task_status_model = apps.get_model("boards", "TaskStatus")
    scheme_status_model = apps.get_model("boards", "BoardSchemeTaskStatus")

    task_status_model.objects.filter(slug="cancel").update(is_terminal=True)
    scheme_status_model.objects.filter(slug="cancel").update(is_terminal=True)


class Migration(migrations.Migration):
    dependencies = [
        ("boards", "0023_process_to_done_transition"),
    ]

    operations = [
        migrations.RunPython(mark_cancel_terminal, migrations.RunPython.noop),
    ]
