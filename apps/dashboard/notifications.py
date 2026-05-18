"""Sync persisted in-app notifications from user state (e.g. weight reminders)."""

from django.urls import reverse
from django.utils import timezone

from apps.dashboard.models import Notification, UserSettings


def _weight_overdue_copy(reminder: dict) -> tuple[str, str]:
    threshold = reminder['threshold_days']
    threshold_label = f'{threshold} day{"s" if threshold != 1 else ""}'
    if reminder['last_logged']:
        days = reminder['days_since']
        body = (
            f"You haven't logged your weight in {days} day{'s' if days != 1 else ''}. "
            f"Your reminder is set to every {threshold_label} without a new entry."
        )
    else:
        body = (
            "You haven't logged your weight yet. "
            f"Your reminder is set to every {threshold_label} without a new entry."
        )
    return 'Weight log overdue', body


def sync_weight_reminder_notification(user_settings: UserSettings) -> Notification | None:
    """Create, update, or remove the weight-overdue notification for a user."""
    reminder = user_settings.get_weight_reminder()
    notif = Notification.objects.filter(
        user=user_settings.user,
        notification_type=Notification.TYPE_WEIGHT_LOG_OVERDUE,
    ).first()

    if not reminder:
        if notif:
            notif.delete()
        return None

    title, message = _weight_overdue_copy(reminder)
    action_url = reverse('dashboard:weight_create')
    metadata = {
        'threshold_days': reminder['threshold_days'],
        'days_since': reminder['days_since'],
        'last_logged': reminder['last_logged'].isoformat() if reminder['last_logged'] else None,
    }

    if notif:
        if not notif.is_dismissed:
            notif.title = title
            notif.message = message
            notif.action_url = action_url
            notif.action_label = 'Log weight'
            notif.metadata = metadata
            notif.save(
                update_fields=[
                    'title',
                    'message',
                    'action_url',
                    'action_label',
                    'metadata',
                    'updated_at',
                ],
            )
        return notif

    notif = Notification.objects.create(
        user=user_settings.user,
        notification_type=Notification.TYPE_WEIGHT_LOG_OVERDUE,
        title=title,
        message=message,
        icon='scale-balanced',
        action_url=action_url,
        action_label='Log weight',
        metadata=metadata,
    )
    maybe_send_weight_reminder_email(notif, user_settings, created=True)
    return notif


def sync_user_notifications(user) -> list[Notification]:
    """Refresh system notifications and return active (non-dismissed) alerts."""
    user_settings, _ = UserSettings.objects.get_or_create(user=user)
    sync_weight_reminder_notification(user_settings)
    return list(
        Notification.objects.filter(user=user, is_dismissed=False).order_by('-created_at'),
    )


def dismiss_notification(notification: Notification) -> None:
    notification.is_dismissed = True
    notification.is_read = True
    notification.save(update_fields=['is_dismissed', 'is_read', 'updated_at'])


def maybe_send_weight_reminder_email(
    notification: Notification,
    user_settings: UserSettings,
    *,
    created: bool,
) -> None:
    """Enqueue a one-time email when a new weight-overdue alert is created."""
    if not created or notification.email_sent_at:
        return
    if not user_settings.notify_updates:
        return
    from apps.dashboard.tasks import send_weight_reminder_email

    send_weight_reminder_email.enqueue(
        notification.user.email,
        notification.title,
        notification.message,
        notification.action_url,
    )
    notification.email_sent_at = timezone.now()
    notification.save(update_fields=['email_sent_at', 'updated_at'])
