from apps.boards.models import Board, BoardColumn, SystemType


def resolve_terminal_column(board: Board) -> BoardColumn | None:
    done_column = (
        BoardColumn.objects.filter(
            board=board,
            is_active=True,
            system_type=SystemType.DONE,
        )
        .order_by("position")
        .first()
    )
    if done_column is not None:
        return done_column

    ready_column = (
        BoardColumn.objects.filter(
            board=board,
            is_active=True,
            system_type=SystemType.READY,
        )
        .order_by("position")
        .first()
    )
    if ready_column is not None:
        return ready_column

    return (
        BoardColumn.objects.filter(board=board, is_active=True)
        .order_by("-position")
        .first()
    )
