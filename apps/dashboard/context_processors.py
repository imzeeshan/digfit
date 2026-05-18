"""Template context processors for the dashboard app."""

from apps.dashboard.notifications import sync_user_notifications


def dashboard_notifications(request):
    """Sync and expose active in-app notifications on dashboard and landing pages."""
    if not request.user.is_authenticated:
        return {}
    match = getattr(request, 'resolver_match', None)
    if not match or match.namespace not in ('dashboard', 'landing'):
        return {}
    notifications = sync_user_notifications(request.user)
    return {
        'dashboard_notifications': notifications,
        'notification_count': len(notifications),
    }
