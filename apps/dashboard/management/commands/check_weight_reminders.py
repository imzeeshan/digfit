"""Check all users for overdue weight logs and print a summary.

Run periodically (e.g. daily via cron) to identify users who haven't
logged their weight within their configured reminder window.

    python manage.py check_weight_reminders
"""

from django.core.management.base import BaseCommand

from apps.dashboard.models import UserSettings
from apps.dashboard.notifications import sync_user_notifications


class Command(BaseCommand):
    help = 'List users who have not logged weight within their reminder window.'

    def handle(self, *args, **options):
        overdue = 0
        for us in UserSettings.objects.select_related('user').filter(weight_reminder_days__gt=0):
            sync_user_notifications(us.user)
            reminder = us.get_weight_reminder()
            if reminder:
                overdue += 1
                days = reminder['days_since']
                label = f"{days} days ago" if days is not None else "never"
                self.stdout.write(
                    self.style.WARNING(f"  {us.user.email}: last weighed {label} "
                                       f"(threshold: {reminder['threshold_days']}d)")
                )
        if overdue:
            self.stdout.write(self.style.WARNING(f"\n{overdue} user(s) overdue."))
        else:
            self.stdout.write(self.style.SUCCESS("All users are up to date."))
