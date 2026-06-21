from dataclasses import dataclass

from django.contrib.auth.models import AbstractBaseUser
from rest_framework.request import Request

from apps.core.models import ApiKey
from apps.tasks.models import ActorType, Task, TaskEvent, TaskEventType, TaskSource

type EventPayload = dict[str, str | int | bool | None]


@dataclass(frozen=True)
class EventActor:
    actor_type: ActorType
    actor_id: str
    source: TaskSource


def resolve_request_context(request: Request) -> EventActor:
    if isinstance(request.auth, ApiKey):
        return EventActor(ActorType.API, request.auth.prefix, TaskSource.API)

    user = request.user
    if isinstance(user, AbstractBaseUser) and user.is_authenticated:
        return EventActor(ActorType.USER, str(user.pk), TaskSource.UI)

    return EventActor(ActorType.SYSTEM, "", TaskSource.SYSTEM)


def record_task_event(
    task: Task,
    event_type: TaskEventType,
    *,
    actor: EventActor,
    payload: EventPayload | None = None,
) -> TaskEvent:
    return TaskEvent.objects.create(
        task=task,
        event_type=event_type,
        actor_type=actor.actor_type,
        actor_id=actor.actor_id,
        source=actor.source,
        payload=payload or {},
    )


def record_request_event(
    task: Task,
    event_type: TaskEventType,
    request: Request,
    payload: EventPayload | None = None,
) -> TaskEvent:
    return record_task_event(
        task,
        event_type,
        actor=resolve_request_context(request),
        payload=payload,
    )
