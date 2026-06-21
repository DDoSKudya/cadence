from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("tasks", "0001_initial"),
    ]

    operations = [
        migrations.RenameIndex(
            model_name="task",
            new_name="idx_task_brd_col_pos_act",
            old_name="idx_tasks_board_column_position_active",
        ),
        migrations.RenameIndex(
            model_name="task",
            new_name="idx_task_col_entered_act",
            old_name="idx_tasks_column_entered_active",
        ),
    ]
