import hmac

from django.contrib.auth import get_user_model
from rest_framework.authentication import BaseAuthentication


class MCPTokenAuthentication(BaseAuthentication):
    """Authenticate requests carrying a valid MCP internal token.

    When the token matches, the request is authenticated as the first
    superuser so that existing permission and queryset guards (is_staff,
    IsAdminUser, etc.) work transparently for MCP tool calls.
    """

    def authenticate(self, request):
        from django_drf_mcp.tokens import HEADER_NAME, get_token

        meta_key = "HTTP_" + HEADER_NAME.upper().replace("-", "_")
        token = request.META.get(meta_key)

        if token is None:
            return None

        if not hmac.compare_digest(token, get_token()):
            return None

        User = get_user_model()
        user = User.objects.filter(is_superuser=True).first()
        if user is None:
            return None

        return (user, "mcp-internal")
