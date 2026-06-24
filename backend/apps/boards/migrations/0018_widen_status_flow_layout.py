from django.db import migrations

STATUS_LAYOUT = {
    "open": (60, 60),
    "ready_on_develop": (340, 60),
    "process": (620, 60),
    "testing": (900, 60),
    "done": (1180, 60),
    "cancel": (760, 300),
}


def widen_status_flow_layout(apps, schema_editor):
    task_status_model = apps.get_model("boards", "TaskStatus")
    for slug, (layout_x, layout_y) in STATUS_LAYOUT.items():
        task_status_model.objects.filter(slug=slug).update(
            layout_x=layout_x,
            layout_y=layout_y,
        )


def noop_reverse(apps, schema_editor):
    return None


class Migration(migrations.Migration):
    dependencies = [
        ("boards", "0017_reseed_workflow_status_graph"),
    ]

    operations = [
        migrations.RunPython(widen_status_flow_layout, noop_reverse),
    ]
