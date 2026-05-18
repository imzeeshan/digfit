from decimal import Decimal

from django.utils import timezone

from apps.dashboard.models import Weight


def seed_weights(users, stdout, style):
    """Weight history for demo user and a recent entry for admin."""
    demo_user = users['user']
    admin = users['admin']

    if Weight.objects.filter(user=demo_user).count() < 8:
        now = timezone.now()
        base = Decimal('188.5')
        sources = ['manual', 'manual', 'api', 'device', 'manual', 'api', 'manual', 'device', 'manual', 'manual']
        for i, days_ago in enumerate([58, 52, 45, 38, 31, 24, 17, 10, 4, 1]):
            value = base - Decimal(i) * Decimal('0.65')
            Weight.objects.get_or_create(
                user=demo_user,
                datetime=now - timezone.timedelta(days=days_ago, hours=9),
                defaults={
                    'value': value,
                    'source': sources[i],
                    'metadata': {'seed': True},
                },
            )
        stdout.write(style.SUCCESS(f'Weight entries seeded for {demo_user.email}'))

    if not Weight.objects.filter(user=admin).exists():
        Weight.objects.create(
            user=admin,
            datetime=timezone.now() - timezone.timedelta(days=2),
            value=Decimal('172.0'),
            source='manual',
            metadata={'seed': True},
        )
        stdout.write(style.SUCCESS(f'Weight entry seeded for {admin.email}'))
