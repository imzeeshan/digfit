"""Sync in-app notifications for all users (e.g. weight overdue alerts).

    python manage.py sync_notifications
"""

from django.core.management.base import BaseCommand

from apps.dashboard.models import UserSettings
from apps.dashboard.notifications import sync_user_notifications


class Command(BaseCommand):
    help = 'Sync persisted notifications (weight reminders, etc.) for all users.'

    def handle(self, *args, **options):
        count = 0
        for us in UserSettings.objects.select_related('user').iterator():
            active = sync_user_notifications(us.user)
            if active:
                count += 1
                self.stdout.write(
                    self.style.WARNING(
                        f"  {us.user.email}: {len(active)} active notification(s)",
                    ),
                )
        if count:
            self.stdout.write(self.style.WARNING(f"\n{count} user(s) with active notifications."))
        else:
            self.stdout.write(self.style.SUCCESS('No active notifications.'))
