MAX_BOARD_SCHEMES = 4
MAX_BOARD_COLUMNS = 7
MAX_TASK_STATUSES = 20


def board_limits_payload() -> dict[str, int]:
    return {
        "max_schemes": MAX_BOARD_SCHEMES,
        "max_columns": MAX_BOARD_COLUMNS,
        "max_task_statuses": MAX_TASK_STATUSES,
    }
