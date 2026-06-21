from django.contrib.auth.models import AnonymousUser
from rest_framework.authentication import BaseAuthentication, get_authorization_header
from rest_framework.exceptions import AuthenticationFailed

from apps.core.models import ApiKey


class ApiKeyAuthentication(BaseAuthentication):
    keyword = "Api-Key"

    def authenticate(self, request):
        header = get_authorization_header(request).decode("utf-8")
        prefix = f"{self.keyword} "

        if not header.startswith(prefix):
            return None

        api_key = ApiKey.verify(header.removeprefix(prefix).strip())
        if api_key is None:
            raise AuthenticationFailed("Invalid API key.")

        return AnonymousUser(), api_key
