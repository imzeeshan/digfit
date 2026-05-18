from django.utils import timezone

from apps.dashboard.models import UserSettings


def seed_user_settings(users, plans, stdout, style):
    """Attach subscription and reminder settings to demo users."""
    now = timezone.now()
    free = plans['free']
    pro = plans['pro']

    configs = [
        (
            users['admin'],
            {
                'subscription_plan': pro,
                'subscription_status': 'active',
                'subscription_start_date': now,
                'subscription_end_date': now + timezone.timedelta(days=30),
                'weight_reminder_days': 5,
                'notify_updates': True,
            },
        ),
        (
            users['coach'],
            {
                'subscription_plan': free,
                'subscription_status': 'inactive',
                'weight_reminder_days': 0,
            },
        ),
        (
            users['user'],
            {
                'subscription_plan': free,
                'subscription_status': 'inactive',
                'weight_reminder_days': 5,
                'notify_updates': True,
            },
        ),
        (
            users['client2'],
            {
                'subscription_plan': None,
                'subscription_status': 'trial',
                'trial_end_date': now + timezone.timedelta(days=14),
                'weight_reminder_days': 5,
                'notify_updates': True,
            },
        ),
    ]

    for user, defaults in configs:
        settings, created = UserSettings.objects.get_or_create(user=user)
        changed = False
        for field, value in defaults.items():
            if getattr(settings, field) != value:
                setattr(settings, field, value)
                changed = True
        if changed or created:
            settings.save()
        label = 'created' if created else 'updated'
        stdout.write(style.SUCCESS(f'Settings for {user.email} {label}'))
