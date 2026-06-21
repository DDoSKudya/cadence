from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("boards", "0003_boardcolumn_idx_board_columns_board_active_position_and_more"),
    ]

    operations = [
        migrations.RenameIndex(
            model_name="boardcolumn",
            new_name="idx_bcol_board_act_pos",
            old_name="idx_board_columns_board_active_position",
        ),
    ]
