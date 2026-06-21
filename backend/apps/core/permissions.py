from rest_framework.permissions import BasePermission

from apps.core.models import ApiKey


class IsSessionAuthenticatedOrApiKey(BasePermission):
    def has_permission(self, request, view) -> bool:
        return bool(request.user and request.user.is_authenticated) or isinstance(
            request.auth,
            ApiKey,
        )
