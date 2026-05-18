from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.db import connection
from django.db.utils import ProgrammingError

from apps.dashboard.management.seeders import (
    seed_interventions,
    seed_meal_plans,
    seed_plans,
    seed_user_settings,
    seed_users,
    seed_weights,
)
from apps.dashboard.notifications import sync_user_notifications


class Command(BaseCommand):
    help = (
        'Seed the database with demo data (users, plans, weights, meals, interventions). '
        'Full seed runs by default; pass --minimal for users and plans only.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--minimal',
            action='store_true',
            help='Only seed users and subscription plans (legacy behavior).',
        )
        parser.add_argument(
            '--skip-migrate',
            action='store_true',
            help='Do not auto-run migrations if tables are missing.',
        )

    def _ensure_migrated(self, *, skip_migrate: bool) -> None:
        required = {'accounts_customuser', 'dashboard_subscriptionplan'}
        existing = set(connection.introspection.table_names())
        if required.issubset(existing):
            return
        if skip_migrate:
            missing = ', '.join(sorted(required - existing))
            raise ProgrammingError(
                f'Database tables are missing ({missing}). Run: python manage.py migrate'
            )
        self.stdout.write(self.style.WARNING('Database not migrated — running migrate…'))
        call_command('migrate', verbosity=1)

    def handle(self, *args, **options):
        minimal = options['minimal']
        self._ensure_migrated(skip_migrate=options['skip_migrate'])

        users = seed_users(self.stdout, self.style)
        plans = seed_plans(self.stdout, self.style)

        if minimal:
            self.stdout.write(self.style.SUCCESS('\nMinimal seed complete (users + plans).'))
            return

        seed_user_settings(users, plans, self.stdout, self.style)
        seed_weights(users, self.stdout, self.style)
        seed_meal_plans(users['user'], self.stdout, self.style)
        seed_interventions(users['user'], self.stdout, self.style)

        for user in users.values():
            sync_user_notifications(user)

        self.stdout.write(self.style.SUCCESS('\nFull seed complete!'))
        self.stdout.write(
            'Demo logins: admin@example.com / admin123 | '
            'coach@example.com / coach123 (staff) | '
            'user@example.com / user1234 | '
            'client2@example.com / client2123 (trial, weight reminder)',
        )
