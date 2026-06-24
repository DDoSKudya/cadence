import django.db.models.deletion
from django.db import migrations, models


def assign_tags_to_default_scheme(apps, schema_editor):
    tag_model = apps.get_model("core", "Tag")
    scheme_model = apps.get_model("boards", "BoardScheme")
    scheme = scheme_model.objects.filter(slug="default").first()
    if scheme is None:
        return
    tag_model.objects.filter(scheme__isnull=True).update(scheme_id=scheme.id)


class Migration(migrations.Migration):
    dependencies = [
        ("boards", "0018_widen_status_flow_layout"),
        ("core", "0007_board_scheme"),
    ]

    operations = [
        migrations.AddField(
            model_name="tag",
            name="scheme",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="tags",
                to="boards.boardscheme",
            ),
        ),
        migrations.RunPython(assign_tags_to_default_scheme, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="tag",
            name="scheme",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="tags",
                to="boards.boardscheme",
            ),
        ),
        migrations.AlterField(
            model_name="tag",
            name="slug",
            field=models.SlugField(blank=True, max_length=60),
        ),
        migrations.AddConstraint(
            model_name="tag",
            constraint=models.UniqueConstraint(
                fields=("scheme", "slug"),
                name="uq_tag_scheme_slug",
            ),
        ),
    ]
