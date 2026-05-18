from decimal import Decimal

from django.utils import timezone

from apps.dashboard.models import Intervention


def seed_interventions(user, stdout, style):
    """Sample interventions across statuses for the primary demo user."""
    if Intervention.objects.filter(user=user).count() >= 4:
        stdout.write(f'Interventions for {user.email} already exist')
        return

    now = timezone.now()
    samples = [
        {
            'type': 'dietary',
            'status': 'active',
            'priority': 'high',
            'title': 'Increase daily protein',
            'description': 'Aim for 150g protein on training days.',
            'trigger_source': 'meal_plan_review',
            'target_metric': 'daily_protein_g',
            'target_value': Decimal('150'),
            'current_value': Decimal('128'),
            'created_by': 'coach',
        },
        {
            'type': 'exercise',
            'status': 'pending',
            'priority': 'normal',
            'title': 'Add two strength sessions',
            'description': 'Schedule upper/lower splits this week.',
            'trigger_source': 'onboarding',
            'scheduled_at': now + timezone.timedelta(days=2),
            'created_by': 'coach',
        },
        {
            'type': 'behavioral',
            'status': 'completed',
            'priority': 'normal',
            'title': 'Log meals for 7 days',
            'description': 'Build consistency with food logging.',
            'trigger_source': 'habit_streak',
            'completed_at': now - timezone.timedelta(days=1),
            'created_by': 'system',
        },
        {
            'type': 'supplement',
            'status': 'cancelled',
            'priority': 'low',
            'title': 'Trial omega-3 stack',
            'description': 'Client opted to postpone supplementation.',
            'trigger_source': 'coach_note',
            'created_by': 'coach',
        },
    ]

    for data in samples:
        Intervention.objects.get_or_create(
            user=user,
            title=data['title'],
            defaults=data,
        )

    stdout.write(style.SUCCESS(f'Interventions seeded for {user.email}'))
