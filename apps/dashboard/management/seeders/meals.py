from datetime import time, timedelta
from decimal import Decimal

from django.utils import timezone

from apps.dashboard.models import MealEntry, MealPlan, UserMeal

PLAN_TITLE = 'Cutting Week 1'

DAY_MEALS = [
    ('breakfast', '08:00', 'Greek yogurt bowl', 420, 32, 45, 12),
    ('lunch', '12:30', 'Chicken rice bowl', 580, 48, 52, 14),
    ('evening_snack', '16:00', 'Protein shake + banana', 280, 28, 35, 4),
    ('dinner', '19:00', 'Salmon + roasted vegetables', 520, 42, 28, 22),
]


def seed_user_meals(user, stdout, style):
    """Logged meals for the primary demo user (last 7 days)."""
    if UserMeal.objects.filter(user=user).count() >= 10:
        return

    now = timezone.now()
    created = 0
    for day_offset in range(7):
        day_start = (now - timedelta(days=day_offset)).replace(
            hour=8, minute=0, second=0, microsecond=0,
        )
        for meal_idx, (meal_type, time_str, title, cal, *_rest) in enumerate(DAY_MEALS[:3]):
            hour, minute = map(int, time_str.split(':'))
            taken = day_start.replace(hour=hour, minute=minute) + timedelta(hours=meal_idx)
            _, was_created = UserMeal.objects.get_or_create(
                user=user,
                title=title,
                time_taken=taken,
                defaults={
                    'meal_type': meal_type,
                    'calories': cal,
                    'description': f'Seeded demo meal — {title}',
                    'metadata': {'seed': True},
                },
            )
            if was_created:
                created += 1

    if created:
        stdout.write(style.SUCCESS(f'{created} user meals seeded for {user.email}'))


def seed_meal_plans(user, stdout, style):
    """7-day meal plan with entries; links some rows to logged meals."""
    seed_user_meals(user, stdout, style)

    today = timezone.localdate()
    start = today - timedelta(days=6)
    end = today

    plan, plan_created = MealPlan.objects.get_or_create(
        user=user,
        title=PLAN_TITLE,
        defaults={
            'start_date': start,
            'end_date': end,
            'daily_calorie_target': 2000,
            'daily_protein_target': Decimal('150'),
            'daily_carbs_target': Decimal('180'),
            'daily_fat_target': Decimal('65'),
            'daily_water_target_ml': 2500,
            'dietary_preference': 'high_protein',
            'allergies_restrictions': ['peanuts'],
            'supplements': ['vitamin D', 'creatine'],
            'goal': 'fat_loss',
            'notes': 'Seeded demo plan for local development.',
        },
    )
    if not plan_created:
        plan.start_date = start
        plan.end_date = end
        plan.save(update_fields=['start_date', 'end_date', 'updated_at'])

    if plan.entries.count() >= 20:
        stdout.write(f'Meal plan "{PLAN_TITLE}" already has entries')
        return

    logged_meals = list(UserMeal.objects.filter(user=user).order_by('time_taken')[:28])
    meal_idx = 0
    entries_created = 0

    for day_num in range(1, 8):
        for sort_order, (meal_type, time_str, title, cal, protein, carbs, fat) in enumerate(DAY_MEALS):
            hour, minute = map(int, time_str.split(':'))
            link = None
            if meal_idx < len(logged_meals) and meal_idx % 2 == 0:
                link = logged_meals[meal_idx]
                meal_idx += 1

            _, created = MealEntry.objects.get_or_create(
                meal_plan=plan,
                day_number=day_num,
                meal_type=meal_type,
                title=title,
                defaults={
                    'scheduled_time': time(hour, minute),
                    'foods_json': [{'name': title, 'quantity': '1 serving'}],
                    'calories': cal,
                    'protein': Decimal(str(protein)),
                    'carbs': Decimal(str(carbs)),
                    'fat': Decimal(str(fat)),
                    'portion_notes': 'As listed',
                    'sort_order': sort_order,
                    'actual_meal': link,
                },
            )
            if created:
                entries_created += 1

    label = 'created' if plan_created else 'updated'
    stdout.write(
        style.SUCCESS(
            f'Meal plan "{PLAN_TITLE}" {label} ({entries_created} entries added)',
        ),
    )
