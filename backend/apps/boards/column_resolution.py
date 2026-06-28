from apps.boards.models import Board, BoardColumn


def resolve_terminal_column(board: Board) -> BoardColumn | None:
    return (
        BoardColumn.objects.filter(board=board, is_active=True)
        .order_by("-position")
        .first()
    )
