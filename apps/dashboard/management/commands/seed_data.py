from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from apps.dashboard.models import SubscriptionPlan

User = get_user_model()


class Command(BaseCommand):
    help = 'Seed the database with initial data (admin user + subscription plans)'

    def handle(self, *args, **options):
        # Create admin user
        user, created = User.objects.get_or_create(
            email='admin@example.com',
            defaults={'is_staff': True, 'is_superuser': True, 'name': 'Admin', 'role': 'admin'},
        )
        if created:
            user.set_password('admin123')
            user.save()
            self.stdout.write(self.style.SUCCESS('Admin user created (admin@example.com / admin123)'))
        else:
            self.stdout.write('Admin user already exists')

        # Create demo coach
        coach, created = User.objects.get_or_create(
            email='coach@example.com',
            defaults={
                'is_staff': False,
                'name': 'Demo Coach',
                'role': 'coach',
                'metadata': {
                    'speciality': 'Strength & Conditioning',
                    'years_of_experience': 5,
                },
            },
        )
        if created:
            coach.set_password('coach123')
            coach.save()
            self.stdout.write(self.style.SUCCESS('Coach user created (coach@example.com / coach123)'))
        else:
            self.stdout.write('Coach user already exists')

        # Create demo regular user
        regular, created = User.objects.get_or_create(
            email='user@example.com',
            defaults={'is_staff': False, 'name': 'Demo User', 'role': 'user'},
        )
        if created:
            regular.set_password('user1234')
            regular.save()
            self.stdout.write(self.style.SUCCESS('Regular user created (user@example.com / user1234)'))
        else:
            self.stdout.write('Regular user already exists')

        # Create subscription plans
        plans = [
            {
                'name': 'Free',
                'slug': 'free',
                'description': 'Get started with the basics',
                'price': 0,
                'interval': 'monthly',
                'features': ['Basic access', 'Community support', '1 project'],
            },
            {
                'name': 'Pro',
                'slug': 'pro',
                'description': 'For growing teams and businesses',
                'price': 9.99,
                'interval': 'monthly',
                'features': ['Everything in Free', 'Priority support', 'API access', '10 projects', 'Analytics'],
            },
            {
                'name': 'Enterprise',
                'slug': 'enterprise',
                'description': 'For large-scale operations',
                'price': 49.99,
                'interval': 'monthly',
                'features': [
                    'Everything in Pro',
                    'Dedicated support',
                    'Custom integrations',
                    'Unlimited projects',
                    'SLA guarantee',
                ],
            },
        ]

        for plan_data in plans:
            plan, created = SubscriptionPlan.objects.get_or_create(
                slug=plan_data['slug'],
                defaults=plan_data,
            )
            status = 'created' if created else 'already exists'
            self.stdout.write(self.style.SUCCESS(f'Plan "{plan.name}" {status}'))

        self.stdout.write(self.style.SUCCESS('\nSeed data complete!'))
