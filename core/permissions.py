from rest_framework.permissions import BasePermission


class IsAuthenticatedOrMCP(BasePermission):
    """Allow access if the user is authenticated OR the request carries a valid MCP internal token."""

    def has_permission(self, request, view):
        if request.user and request.user.is_authenticated:
            return True

        from django_drf_mcp.permissions import IsMCPInternalRequest
        return IsMCPInternalRequest().has_permission(request, view)
