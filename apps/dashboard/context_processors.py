"""Template context processors for the dashboard app."""


def weight_reminder(request):
    """Expose weight log reminder on all dashboard pages (not only Overview)."""
    if not request.user.is_authenticated:
        return {}
    match = getattr(request, 'resolver_match', None)
    if not match or match.namespace != 'dashboard':
        return {}
    from apps.dashboard.models import UserSettings

    user_settings, _ = UserSettings.objects.get_or_create(user=request.user)
    return {'weight_reminder': user_settings.get_weight_reminder()}
