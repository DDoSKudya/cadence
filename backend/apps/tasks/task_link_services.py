from __future__ import annotations

from dataclasses import dataclass

from django.db import transaction
from rest_framework.exceptions import ValidationError

from apps.tasks.models import Task, TaskLink, TaskLinkType


@dataclass(frozen=True)
class TaskLinkInput:
    target_task_id: int
    link_type: str


class TaskLinkService:
    @staticmethod
    def serialize_for_task(task: Task) -> list[dict[str, object]]:
        outgoing = task.outgoing_links.select_related("to_task")
        incoming = task.incoming_links.select_related("from_task")

        links: list[dict[str, object]] = []
        for link in outgoing:
            links.append(
                TaskLinkService._serialize_edge(
                    link=link,
                    other=link.to_task,
                    direction="outgoing",
                ),
            )
        for link in incoming:
            links.append(
                TaskLinkService._serialize_edge(
                    link=link,
                    other=link.from_task,
                    direction="incoming",
                ),
            )
        links.sort(key=lambda item: (str(item["link_type"]), str(item["title"])))
        return links

    @staticmethod
    def link_count(task: Task) -> int:
        return task.outgoing_links.count() + task.incoming_links.count()

    @staticmethod
    @transaction.atomic
    def sync_outgoing_links(task: Task, links: list[TaskLinkInput]) -> None:
        TaskLink.objects.filter(from_task=task).delete()
        if not links:
            return

        seen: set[tuple[int, str]] = set()
        to_create: list[TaskLink] = []
        for item in links:
            key = (item.target_task_id, item.link_type)
            if key in seen:
                continue
            seen.add(key)

            if item.target_task_id == task.id:
                raise ValidationError("Task cannot link to itself.")

            if item.link_type not in TaskLinkType.values:
                raise ValidationError("Task link type is invalid.")

            target = Task.objects.filter(
                pk=item.target_task_id,
                board_id=task.board_id,
                archived_at__isnull=True,
            ).first()
            if target is None:
                raise ValidationError("Linked task is invalid.")

            to_create.append(
                TaskLink(
                    from_task=task,
                    to_task=target,
                    link_type=item.link_type,
                ),
            )

        if to_create:
            TaskLink.objects.bulk_create(to_create)

    @staticmethod
    def _serialize_edge(
        *,
        link: TaskLink,
        other: Task,
        direction: str,
    ) -> dict[str, object]:
        return {
            "id": link.id,
            "task_id": other.id,
            "title": other.title,
            "task_type": other.task_type,
            "link_type": link.link_type,
            "direction": direction,
        }
