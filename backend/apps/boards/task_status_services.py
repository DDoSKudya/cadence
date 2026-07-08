from __future__ import annotations

from typing import Any

from django.db import transaction
from django.utils.text import slugify
from rest_framework.exceptions import ValidationError

from apps.boards.constants import MAX_TASK_STATUSES, board_limits_payload
from apps.boards.models import (
    Board,
    BoardColumn,
    BoardScheme,
    BoardSchemeTaskStatus,
    BoardSchemeTaskStatusTransition,
    SystemType,
    TaskStatus,
    TaskStatusTransition,
)
from apps.boards.scheme_services import DEFAULT_SCHEME_SLUG, BoardSchemeService
from apps.common.i18n import DEFAULT_LOCALE, t

StatusLayoutDef = tuple[str, str, str, float, float, bool, bool, str, dict[str, Any]]
TransitionDef = tuple[str, str, dict[str, Any]]

WORKFLOW_STATUS_LAYOUT: tuple[StatusLayoutDef, ...] = (
    (
        "open",
        "defaults.status.open",
        "slate",
        60,
        60,
        True,
        False,
        SystemType.BACKLOG,
        {"creation_only": True},
    ),
    (
        "ready_on_develop",
        "defaults.status.readyOnDevelop",
        "blue",
        340,
        60,
        False,
        False,
        SystemType.BACKLOG,
        {},
    ),
    (
        "process",
        "defaults.status.process",
        "amber",
        620,
        60,
        False,
        False,
        SystemType.IN_PROGRESS,
        {"auto_move_column": True},
    ),
    (
        "testing",
        "defaults.status.testing",
        "indigo",
        900,
        60,
        False,
        False,
        SystemType.IN_PROGRESS,
        {"auto_move_column": True},
    ),
    (
        "done",
        "defaults.status.done",
        "green",
        1180,
        60,
        False,
        True,
        SystemType.READY,
        {"auto_move_column": True},
    ),
    (
        "cancel",
        "defaults.status.cancel",
        "red",
        760,
        300,
        False,
        True,
        SystemType.READY,
        {"auto_move_column": True},
    ),
)

WORKFLOW_TRANSITIONS: tuple[TransitionDef, ...] = (
    ("open", "ready_on_develop", {"required_fields": ["description"]}),
    ("ready_on_develop", "process", {"auto_move_column": True}),
    ("process", "testing", {}),
    ("process", "done", {"auto_move_column": True}),
    ("testing", "done", {"auto_move_column": True}),
    ("testing", "process", {}),
    ("testing", "ready_on_develop", {}),
)


def workflow_validation_error(
    message: str,
    code: str,
    **extra: Any,
) -> ValidationError:
    payload: dict[str, Any] = {"detail": message, "code": code}
    payload.update(extra)
    return ValidationError(payload)


WORKFLOW_CANCEL_FROM: tuple[str, ...] = (
    "open",
    "ready_on_develop",
    "process",
    "testing",
)


class TaskStatusService:
    @staticmethod
    def is_enforced(board: Board) -> bool:
        return TaskStatusTransition.objects.filter(board=board).exists()

    @staticmethod
    def get_graph(board: Board) -> dict[str, object]:
        statuses = list(
            TaskStatus.objects.filter(board=board)
            .select_related("column")
            .order_by("position", "name"),
        )
        transitions = TaskStatusTransition.objects.filter(board=board).order_by(
            "from_status_id",
            "to_status_id",
        )
        return {
            "enforced": TaskStatusService.is_enforced(board),
            "statuses": [
                TaskStatusService._serialize_status(status) for status in statuses
            ],
            "transitions": [
                {
                    "from_status_id": transition.from_status_id,
                    "to_status_id": transition.to_status_id,
                    "rules": transition.rules or {},
                }
                for transition in transitions
            ],
            "limits": board_limits_payload(),
        }

    @staticmethod
    def _serialize_status(status: TaskStatus) -> dict[str, object]:
        return {
            "id": status.id,
            "name": status.name,
            "slug": status.slug,
            "color": status.color,
            "layout_x": status.layout_x,
            "layout_y": status.layout_y,
            "on_flow": status.on_flow,
            "position": status.position,
            "is_initial": status.is_initial,
            "is_terminal": status.is_terminal,
            "column_id": status.column_id,
            "column_name": status.column.name if status.column is not None else None,
            "rules": status.rules or {},
        }

    @staticmethod
    @transaction.atomic
    def save_graph(
        board: Board,
        *,
        statuses: list[dict[str, Any]],
        transitions: list[dict[str, Any]],
    ) -> dict[str, object]:
        BoardSchemeService.assert_board_mutable(board)

        if len(statuses) > MAX_TASK_STATUSES:
            raise ValidationError(
                "Task status limit reached.",
                code="task_status_limit",
            )

        key_to_id: dict[str, int] = {}
        kept_ids: set[int] = set()
        seen_slugs: set[str] = set()

        for index, item in enumerate(statuses):
            raw_id = item.get("id")
            client_key = str(item.get("client_key") or "").strip()
            name = str(item.get("name", "")).strip()
            if not name:
                raise ValidationError("Task status name is required.")

            color = str(item.get("color") or "slate")
            layout_x = float(item.get("layout_x") or 0)
            layout_y = float(item.get("layout_y") or 0)
            is_initial = bool(item.get("is_initial"))
            is_terminal = bool(item.get("is_terminal"))
            rules = item.get("rules") if isinstance(item.get("rules"), dict) else {}
            column_id = item.get("column_id")
            column = None
            if column_id is not None:
                column = BoardColumn.objects.filter(
                    board=board,
                    id=column_id,
                    is_active=True,
                ).first()
                if column is None:
                    raise ValidationError("Status column binding is invalid.")

            if raw_id is not None:
                status = TaskStatus.objects.filter(board=board, id=raw_id).first()
                if status is None:
                    raise ValidationError("Task status is invalid.")
                if status.slug in seen_slugs:
                    raise ValidationError("Task status slug must be unique.")
                seen_slugs.add(status.slug)
                status.name = name
                status.color = color
                status.layout_x = layout_x
                status.layout_y = layout_y
                status.on_flow = True
                status.position = index
                status.is_initial = is_initial
                status.is_terminal = is_terminal
                status.rules = rules
                status.column = column
                status.save(
                    update_fields=[
                        "name",
                        "color",
                        "layout_x",
                        "layout_y",
                        "on_flow",
                        "position",
                        "is_initial",
                        "is_terminal",
                        "rules",
                        "column",
                        "updated_at",
                    ],
                )
            else:
                slug = TaskStatusService._unique_slug(
                    board,
                    slugify(name) or "status",
                )
                if slug in seen_slugs:
                    raise ValidationError("Task status slug must be unique.")
                seen_slugs.add(slug)
                status = TaskStatus.objects.create(
                    board=board,
                    name=name,
                    slug=slug,
                    color=color,
                    layout_x=layout_x,
                    layout_y=layout_y,
                    on_flow=True,
                    position=index,
                    is_initial=is_initial,
                    is_terminal=is_terminal,
                    rules=rules,
                    column=column,
                )

            kept_ids.add(status.id)
            key_to_id[str(status.id)] = status.id
            if client_key:
                key_to_id[client_key] = status.id

        removable = TaskStatus.objects.filter(board=board, on_flow=True).exclude(
            id__in=kept_ids,
        )
        for status in removable:
            from apps.tasks.models import Task

            if Task.objects.filter(task_status=status).exists():
                raise ValidationError(
                    f'Status "{status.name}" is used by tasks.',
                )
        removable.delete()

        normalized: list[tuple[int, int, dict[str, Any]]] = []
        seen_pairs: set[tuple[int, int]] = set()
        for item in transitions:
            from_id = TaskStatusService._resolve_status_ref(
                item["from_status_id"],
                key_to_id,
            )
            to_id = TaskStatusService._resolve_status_ref(
                item["to_status_id"],
                key_to_id,
            )
            if from_id == to_id:
                raise ValidationError("Status cannot transition to itself.")
            if from_id not in kept_ids or to_id not in kept_ids:
                raise ValidationError("Transition references an invalid task status.")
            pair = (from_id, to_id)
            if pair in seen_pairs:
                continue
            seen_pairs.add(pair)
            rules_raw = item.get("rules")
            transition_rules: dict[str, Any] = (
                rules_raw if isinstance(rules_raw, dict) else {}
            )
            normalized.append((from_id, to_id, transition_rules))

        TaskStatusTransition.objects.filter(board=board).delete()
        if normalized:
            TaskStatusTransition.objects.bulk_create(
                [
                    TaskStatusTransition(
                        board=board,
                        from_status_id=from_id,
                        to_status_id=to_id,
                        rules=rules,
                    )
                    for from_id, to_id, rules in normalized
                ],
            )

        TaskStatusService.sync_graph_to_scheme(board)
        return TaskStatusService.get_graph(board)

    @staticmethod
    @transaction.atomic
    def save_layout(
        board: Board,
        *,
        statuses: list[dict[str, Any]],
    ) -> dict[str, object]:
        if not statuses:
            return TaskStatusService.get_graph(board)

        status_ids = [int(item["id"]) for item in statuses]
        existing = {
            status.id: status
            for status in TaskStatus.objects.filter(board=board, id__in=status_ids)
        }
        if len(existing) != len(set(status_ids)):
            raise ValidationError("Task status is invalid.")

        for item in statuses:
            status = existing.get(int(item["id"]))
            if status is None:
                raise ValidationError("Task status is invalid.")
            status.layout_x = float(item["layout_x"])
            status.layout_y = float(item["layout_y"])
            status.save(update_fields=["layout_x", "layout_y", "updated_at"])

        TaskStatusService.sync_graph_to_scheme(board)
        return TaskStatusService.get_graph(board)

    @staticmethod
    def sync_graph_to_scheme(
        board: Board,
        *,
        scheme: BoardScheme | None = None,
    ) -> None:
        scheme = scheme or BoardSchemeService.get_active_scheme(board)
        if scheme is None or scheme.is_locked:
            return

        column_positions = {
            column.id: column.position
            for column in BoardColumn.objects.filter(board=board, is_active=True)
        }

        BoardSchemeTaskStatusTransition.objects.filter(scheme=scheme).delete()
        BoardSchemeTaskStatus.objects.filter(scheme=scheme).delete()

        statuses = list(
            TaskStatus.objects.filter(board=board).order_by("position", "name"),
        )
        if not statuses:
            return

        BoardSchemeTaskStatus.objects.bulk_create(
            [
                BoardSchemeTaskStatus(
                    scheme=scheme,
                    slug=status.slug,
                    name=status.name,
                    color=status.color,
                    layout_x=status.layout_x,
                    layout_y=status.layout_y,
                    on_flow=status.on_flow,
                    position=status.position,
                    is_initial=status.is_initial,
                    is_terminal=status.is_terminal,
                    column_position=column_positions.get(status.column_id)
                    if status.column_id
                    else None,
                    rules=status.rules or {},
                )
                for status in statuses
            ],
        )

        slug_by_id = {status.id: status.slug for status in statuses}
        transition_models: list[BoardSchemeTaskStatusTransition] = []
        for transition in TaskStatusTransition.objects.filter(board=board).order_by(
            "from_status_id",
            "to_status_id",
        ):
            from_slug = slug_by_id.get(transition.from_status_id)
            to_slug = slug_by_id.get(transition.to_status_id)
            if from_slug is None or to_slug is None:
                continue
            transition_models.append(
                BoardSchemeTaskStatusTransition(
                    scheme=scheme,
                    from_status_slug=from_slug,
                    to_status_slug=to_slug,
                    rules=transition.rules or {},
                ),
            )
        if transition_models:
            BoardSchemeTaskStatusTransition.objects.bulk_create(transition_models)

    @staticmethod
    @transaction.atomic
    def apply_graph_from_scheme(
        board: Board,
        scheme: BoardScheme,
        *,
        position_to_column: dict[int, BoardColumn],
        columns_by_type: dict[str, BoardColumn],
    ) -> None:
        templates = list(
            BoardSchemeTaskStatus.objects.filter(scheme=scheme).order_by(
                "position",
                "name",
            ),
        )
        if not templates:
            if scheme.slug == DEFAULT_SCHEME_SLUG:
                TaskStatusService.seed_default_graph(board, columns_by_type)
            else:
                TaskStatusService.seed_starter_graph(board, columns_by_type)
            return

        TaskStatusTransition.objects.filter(board_id=board.pk).delete()
        TaskStatus.objects.filter(board_id=board.pk).delete()

        slug_to_status: dict[str, TaskStatus] = {}
        for template in templates:
            column = None
            if template.column_position is not None:
                column = position_to_column.get(template.column_position)
            status = TaskStatus.objects.create(
                board=board,
                name=template.name,
                slug=template.slug,
                color=template.color,
                layout_x=template.layout_x,
                layout_y=template.layout_y,
                on_flow=template.on_flow,
                position=template.position,
                is_initial=template.is_initial,
                is_terminal=template.is_terminal,
                rules=template.rules or {},
                column=column,
            )
            slug_to_status[template.slug] = status

        transition_models: list[TaskStatusTransition] = []
        for transition_template in BoardSchemeTaskStatusTransition.objects.filter(
            scheme=scheme,
        ).order_by("from_status_slug", "to_status_slug"):
            from_status = slug_to_status.get(transition_template.from_status_slug)
            to_status = slug_to_status.get(transition_template.to_status_slug)
            if from_status is None or to_status is None:
                continue
            transition_models.append(
                TaskStatusTransition(
                    board=board,
                    from_status=from_status,
                    to_status=to_status,
                    rules=transition_template.rules or {},
                ),
            )
        if transition_models:
            TaskStatusTransition.objects.bulk_create(transition_models)

    @staticmethod
    def get_initial_status(board: Board) -> TaskStatus | None:
        return (
            TaskStatus.objects.filter(board=board, is_initial=True, on_flow=True)
            .order_by("position")
            .first()
        )

    @staticmethod
    def status_system_type(status: TaskStatus | None) -> str | None:
        if status is None:
            return None
        if status.column_id is not None and status.column is not None:
            return status.column.system_type
        system_type = (status.rules or {}).get("system_type")
        if isinstance(system_type, str) and system_type:
            return system_type
        if status.slug in {choice.value for choice in SystemType}:
            return status.slug
        return None

    @staticmethod
    def resolve_status_for_system_type(
        board: Board,
        *,
        system_types: tuple[str, ...],
        prefer_slugs: tuple[str, ...] = (),
        terminal_only: bool | None = None,
    ) -> TaskStatus | None:
        statuses = list(
            TaskStatus.objects.filter(board=board, on_flow=True)
            .select_related("column")
            .order_by("position")
        )
        matches: list[TaskStatus] = []
        for status in statuses:
            if terminal_only is not None and status.is_terminal != terminal_only:
                continue
            if TaskStatusService.status_system_type(status) in system_types:
                matches.append(status)
        if not matches:
            return None
        if prefer_slugs:
            for slug in prefer_slugs:
                preferred = next(
                    (status for status in matches if status.slug == slug),
                    None,
                )
                if preferred is not None:
                    return preferred
        return matches[0]

    @staticmethod
    def is_done_status(status: TaskStatus | None) -> bool:
        if status is None or not status.is_terminal:
            return False
        if (status.rules or {}).get("semantic") == "done":
            return True
        return status.slug == "done"

    @staticmethod
    def list_allowed_targets(
        *,
        board: Board,
        from_status: TaskStatus | None,
    ) -> list[TaskStatus]:
        if from_status is None or from_status.is_terminal:
            return []

        if not TaskStatusService.is_enforced(board):
            return list(
                TaskStatus.objects.filter(board=board, on_flow=True)
                .exclude(id=from_status.id)
                .order_by("position"),
            )

        to_ids = TaskStatusTransition.objects.filter(
            board=board,
            from_status=from_status,
        ).values_list("to_status_id", flat=True)
        return list(
            TaskStatus.objects.filter(id__in=to_ids, on_flow=True).order_by("position"),
        )

    @staticmethod
    def get_transition(
        *,
        board: Board,
        from_status_id: int,
        to_status_id: int,
    ) -> TaskStatusTransition | None:
        return TaskStatusTransition.objects.filter(
            board=board,
            from_status_id=from_status_id,
            to_status_id=to_status_id,
        ).first()

    @staticmethod
    def is_transition_allowed(
        *,
        board: Board,
        from_status_id: int | None,
        to_status_id: int | None,
    ) -> bool:
        if from_status_id is None or to_status_id is None:
            return True
        if from_status_id == to_status_id:
            return True
        if not TaskStatusService.is_enforced(board):
            return True
        return (
            TaskStatusService.get_transition(
                board=board,
                from_status_id=from_status_id,
                to_status_id=to_status_id,
            )
            is not None
        )

    @staticmethod
    def validate_status_change(
        *,
        task,
        from_status: TaskStatus | None,
        to_status: TaskStatus,
        is_creation: bool = False,
    ) -> None:
        board = task.board

        if from_status and from_status.is_terminal:
            raise workflow_validation_error(
                "Task in a terminal status cannot be moved.",
                "status_terminal",
            )

        to_rules = to_status.rules or {}
        if to_rules.get("creation_only") and not is_creation:
            raise workflow_validation_error(
                "This status can only be assigned when a task is created.",
                "status_creation_only",
            )

        if from_status is None:
            if not is_creation:
                raise ValidationError("Task status is invalid.")
            return

        if from_status.id == to_status.id:
            return

        if not TaskStatusService.is_transition_allowed(
            board=board,
            from_status_id=from_status.id,
            to_status_id=to_status.id,
        ):
            raise workflow_validation_error(
                "Task status transition is not allowed.",
                "status_transition_not_allowed",
                from_status=from_status.name,
                from_status_slug=from_status.slug,
                to_status=to_status.name,
                to_status_slug=to_status.slug,
            )

        transition = TaskStatusService.get_transition(
            board=board,
            from_status_id=from_status.id,
            to_status_id=to_status.id,
        )
        if transition is None:
            return

        required_fields = (transition.rules or {}).get("required_fields", [])
        if not isinstance(required_fields, list):
            required_fields = []
        missing_fields: list[str] = []
        for field_name in required_fields:
            value = getattr(task, field_name, None)
            if value is None or (isinstance(value, str) and not value.strip()):
                missing_fields.append(str(field_name))
        if missing_fields:
            raise workflow_validation_error(
                "Task is missing required fields for this status change.",
                "status_required_fields",
                missing_fields=missing_fields,
            )

    @staticmethod
    def _ready_column_status_preference(
        *,
        source_column: BoardColumn,
        target_column: BoardColumn,
    ) -> str | None:
        if target_column.system_type != SystemType.READY:
            return None
        if source_column.system_type == SystemType.IN_PROGRESS:
            return "done"
        return "cancel"

    @staticmethod
    def resolve_target_status_for_column(
        *,
        task,
        source_status: TaskStatus | None,
        source_column: BoardColumn,
        target_column: BoardColumn,
    ) -> TaskStatus | None:
        if source_status and source_status.is_terminal:
            raise workflow_validation_error(
                "Task in a terminal status cannot be moved.",
                "status_terminal",
            )

        candidates = list(
            TaskStatus.objects.filter(
                board_id=target_column.board_id,
                column_id=target_column.id,
            ).order_by("position"),
        )
        if not candidates:
            return TaskStatusService.resolve_column_status(target_column)

        preferred_slug = TaskStatusService._ready_column_status_preference(
            source_column=source_column,
            target_column=target_column,
        )
        if preferred_slug is not None:
            preferred = next(
                (status for status in candidates if status.slug == preferred_slug),
                None,
            )
            if preferred is not None:
                try:
                    TaskStatusService.validate_status_change(
                        task=task,
                        from_status=source_status,
                        to_status=preferred,
                    )
                    return preferred
                except ValidationError:
                    pass

        allowed: list[TaskStatus] = []
        for candidate in candidates:
            try:
                TaskStatusService.validate_status_change(
                    task=task,
                    from_status=source_status,
                    to_status=candidate,
                )
            except ValidationError:
                continue
            allowed.append(candidate)

        if not allowed:
            return None

        if len(allowed) == 1:
            return allowed[0]

        if preferred_slug == "done":
            allowed.sort(key=lambda status: (status.slug != "done", status.position))
        elif preferred_slug == "cancel":
            allowed.sort(key=lambda status: (status.slug != "cancel", status.position))
        else:
            allowed.sort(
                key=lambda status: (
                    status.slug == "cancel",
                    status.position,
                ),
            )
        return allowed[0]

    @staticmethod
    def can_move_between_columns_via_status(
        *,
        task,
        source_column: BoardColumn,
        target_column: BoardColumn,
    ) -> bool:
        if source_column.id == target_column.id:
            return True

        source_status = task.task_status
        if source_status is None:
            source_status = TaskStatusService.resolve_column_status(source_column)

        return (
            TaskStatusService.resolve_target_status_for_column(
                task=task,
                source_status=source_status,
                source_column=source_column,
                target_column=target_column,
            )
            is not None
        )

    @staticmethod
    def resolve_column_status(column: BoardColumn) -> TaskStatus | None:
        bound = (
            TaskStatus.objects.filter(board_id=column.board_id, column_id=column.id)
            .order_by("position")
            .first()
        )
        if bound is not None:
            return bound
        if column.task_status_id is not None:
            return column.task_status
        return TaskStatus.objects.filter(
            board_id=column.board_id,
            slug=column.system_type,
        ).first()

    @staticmethod
    @transaction.atomic
    def seed_workflow_graph(
        board: Board,
        columns_by_type: dict[str, BoardColumn] | None = None,
    ) -> None:
        board_id = board.pk
        TaskStatusTransition.objects.filter(board_id=board_id).delete()
        TaskStatus.objects.filter(board_id=board_id).delete()

        columns_by_type = columns_by_type or {}
        statuses_by_slug: dict[str, TaskStatus] = {}

        for index, (
            slug,
            label_key,
            color,
            x,
            y,
            is_initial,
            is_terminal,
            column_type,
            rules,
        ) in enumerate(WORKFLOW_STATUS_LAYOUT):
            column = columns_by_type.get(column_type)
            status = TaskStatus.objects.create(
                board_id=board_id,
                name=t(label_key, locale=DEFAULT_LOCALE),
                slug=slug,
                color=color,
                layout_x=x,
                layout_y=y,
                on_flow=True,
                position=index,
                is_initial=is_initial,
                is_terminal=is_terminal,
                rules=rules,
                column_id=column.pk if column is not None else None,
            )
            statuses_by_slug[slug] = status

        transitions: list[TaskStatusTransition] = []
        for from_slug, to_slug, rules in WORKFLOW_TRANSITIONS:
            from_status = statuses_by_slug.get(from_slug)
            to_status = statuses_by_slug.get(to_slug)
            if from_status is None or to_status is None:
                continue
            transitions.append(
                TaskStatusTransition(
                    board_id=board_id,
                    from_status=from_status,
                    to_status=to_status,
                    rules=rules,
                ),
            )

        cancel_status = statuses_by_slug.get("cancel")
        if cancel_status is not None:
            for from_slug in WORKFLOW_CANCEL_FROM:
                from_status = statuses_by_slug.get(from_slug)
                if from_status is None:
                    continue
                transitions.append(
                    TaskStatusTransition(
                        board_id=board_id,
                        from_status=from_status,
                        to_status=cancel_status,
                        rules={"auto_move_column": True},
                    ),
                )

        if transitions:
            TaskStatusTransition.objects.bulk_create(transitions)

    @staticmethod
    @transaction.atomic
    def seed_default_graph(
        board: Board,
        columns_by_type: dict[str, BoardColumn] | None = None,
    ) -> None:
        TaskStatusService.seed_workflow_graph(board, columns_by_type)

    @staticmethod
    @transaction.atomic
    def seed_library_statuses(
        board: Board,
        columns_by_type: dict[str, BoardColumn] | None = None,
    ) -> None:
        board_id = board.pk
        TaskStatusTransition.objects.filter(board_id=board_id).delete()
        TaskStatus.objects.filter(board_id=board_id).delete()

        columns_by_type = columns_by_type or {}
        for index, (
            slug,
            label_key,
            color,
            _x,
            _y,
            is_initial,
            is_terminal,
            column_type,
            rules,
        ) in enumerate(WORKFLOW_STATUS_LAYOUT):
            column = columns_by_type.get(column_type)
            TaskStatus.objects.create(
                board_id=board_id,
                name=t(label_key, locale=DEFAULT_LOCALE),
                slug=slug,
                color=color,
                layout_x=0,
                layout_y=0,
                on_flow=False,
                position=index,
                is_initial=is_initial,
                is_terminal=is_terminal,
                rules=rules,
                column_id=column.pk if column is not None else None,
            )

    @staticmethod
    @transaction.atomic
    def seed_starter_graph(
        board: Board,
        columns_by_type: dict[str, BoardColumn] | None = None,
    ) -> None:
        columns_by_type = columns_by_type or {}
        if not columns_by_type:
            columns_by_type = {
                column.system_type: column
                for column in BoardColumn.objects.filter(
                    board=board,
                    is_active=True,
                )
            }
        TaskStatusService.seed_library_statuses(board, columns_by_type)

    @staticmethod
    def clear_board_graph(board: Board) -> None:
        TaskStatusTransition.objects.filter(board_id=board.pk).delete()
        TaskStatus.objects.filter(board_id=board.pk).delete()

    @staticmethod
    @transaction.atomic
    def sync_column_bindings(column: BoardColumn, task_status_ids: list[int]) -> None:
        from apps.boards.scheme_services import BoardSchemeService

        BoardSchemeService.assert_column_mutable(column)
        board = column.board
        requested_ids = list(dict.fromkeys(task_status_ids))
        valid_ids = set(
            TaskStatus.objects.filter(board=board, id__in=requested_ids).values_list(
                "id",
                flat=True,
            ),
        )
        if len(valid_ids) != len(requested_ids):
            raise ValidationError(
                "Task status binding is invalid.",
                code="status_column_binding_invalid",
            )

        TaskStatus.objects.filter(board=board, column_id=column.id).exclude(
            id__in=valid_ids,
        ).update(column_id=None)
        if valid_ids:
            TaskStatus.objects.filter(board=board, id__in=valid_ids).update(
                column_id=column.id,
            )

    @staticmethod
    def _resolve_status_ref(
        ref: object,
        key_to_id: dict[str, int],
    ) -> int:
        key = str(ref)
        if key in key_to_id:
            return key_to_id[key]
        if key.isdigit():
            return int(key)
        raise ValidationError("Transition references an invalid task status.")

    @staticmethod
    def _unique_slug(board: Board, base: str, exclude_id: int | None = None) -> str:
        slug = base[:60] or "status"
        queryset = TaskStatus.objects.filter(board=board, slug=slug)
        if exclude_id is not None:
            queryset = queryset.exclude(id=exclude_id)
        if not queryset.exists():
            return slug

        index = 2
        while True:
            candidate = f"{base[:55]}-{index}"
            queryset = TaskStatus.objects.filter(board=board, slug=candidate)
            if exclude_id is not None:
                queryset = queryset.exclude(id=exclude_id)
            if not queryset.exists():
                return candidate
            index += 1
