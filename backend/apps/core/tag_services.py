from __future__ import annotations

from django.utils.text import slugify
from rest_framework.exceptions import ValidationError

from apps.boards.models import Board, BoardScheme
from apps.boards.scheme_services import BoardSchemeService
from apps.boards.services import ColumnSettingsService
from apps.core.models import Tag


class TagService:
    @staticmethod
    def get_active_scheme() -> BoardScheme:
        board = ColumnSettingsService.get_default_board()
        scheme = BoardSchemeService.get_active_scheme(board)
        if scheme is None:
            return BoardSchemeService.ensure_default_scheme()
        return scheme

    @staticmethod
    def get_scheme_for_board(board: Board) -> BoardScheme:
        scheme = BoardSchemeService.get_active_scheme(board)
        if scheme is None:
            return BoardSchemeService.ensure_default_scheme()
        return scheme

    @staticmethod
    def queryset_for_scheme(scheme: BoardScheme):
        return Tag.objects.filter(scheme=scheme, is_active=True).order_by("name")

    @staticmethod
    def queryset_for_active_scheme():
        return TagService.queryset_for_scheme(TagService.get_active_scheme())

    @staticmethod
    def resolve_slugs(*, scheme: BoardScheme, tag_slugs: list[str]) -> list[Tag]:
        if not tag_slugs:
            return []

        tags = list(
            Tag.objects.filter(
                scheme=scheme,
                slug__in=tag_slugs,
                is_active=True,
            ),
        )
        found_slugs = {tag.slug for tag in tags}
        missing = [slug for slug in tag_slugs if slug not in found_slugs]
        if missing:
            raise ValidationError(f"Unknown tags: {', '.join(missing)}")
        return tags

    @staticmethod
    def resolve_slugs_for_board(*, board: Board, tag_slugs: list[str]) -> list[Tag]:
        return TagService.resolve_slugs(
            scheme=TagService.get_scheme_for_board(board),
            tag_slugs=tag_slugs,
        )

    @staticmethod
    def get_or_create_by_name(*, scheme: BoardScheme, name: str) -> Tag:
        cleaned = name.strip()
        slug = slugify(cleaned) or cleaned.lower()
        tag, created = Tag.objects.get_or_create(
            scheme=scheme,
            slug=slug,
            defaults={"name": cleaned},
        )
        if not created and tag.name != cleaned:
            tag.name = cleaned
            tag.save(update_fields=["name"])
        return tag
