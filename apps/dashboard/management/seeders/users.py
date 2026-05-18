from datetime import date

from django.contrib.auth import get_user_model

User = get_user_model()

DEMO_EMAILS = {
    'admin': 'admin@example.com',
    'coach': 'coach@example.com',
    'user': 'user@example.com',
    'client2': 'client2@example.com',
}


def _ensure_password(user, password, *, created):
    if created:
        user.set_password(password)
        user.save(update_fields=['password'])


def seed_users(stdout, style):
    """Create demo users; return dict keyed by role alias."""
    users = {}

    admin, created = User.objects.get_or_create(
        email=DEMO_EMAILS['admin'],
        defaults={
            'is_staff': True,
            'is_superuser': True,
            'name': 'Admin',
            'role': 'admin',
        },
    )
    _ensure_password(admin, 'admin123', created=created)
    users['admin'] = admin
    if created:
        stdout.write(style.SUCCESS('Admin user created (admin@example.com / admin123)'))
    else:
        stdout.write('Admin user already exists')

    coach, created = User.objects.get_or_create(
        email=DEMO_EMAILS['coach'],
        defaults={
            'is_staff': True,
            'name': 'Demo Coach',
            'role': 'coach',
            'metadata': {
                'speciality': 'Strength & Conditioning',
                'years_of_experience': 5,
            },
        },
    )
    _ensure_password(coach, 'coach123', created=created)
    if not coach.is_staff:
        coach.is_staff = True
        coach.save(update_fields=['is_staff'])
    users['coach'] = coach
    if created:
        stdout.write(style.SUCCESS('Coach user created (coach@example.com / coach123, staff)'))
    else:
        stdout.write('Coach user already exists')

    demo_user, created = User.objects.get_or_create(
        email=DEMO_EMAILS['user'],
        defaults={
            'is_staff': False,
            'name': 'Demo User',
            'role': 'user',
            'date_of_birth': date(1994, 6, 15),
            'gender': 'male',
            'metadata': {
                'goal': 'fat_loss',
                'height_cm': 178,
                'activity_level': 'moderate',
            },
        },
    )
    _ensure_password(demo_user, 'user1234', created=created)
    if not created:
        demo_user.name = demo_user.name or 'Demo User'
        demo_user.date_of_birth = demo_user.date_of_birth or date(1994, 6, 15)
        demo_user.gender = demo_user.gender or 'male'
        demo_user.metadata = {**demo_user.metadata, 'goal': 'fat_loss', 'height_cm': 178, 'activity_level': 'moderate'}
        demo_user.save(update_fields=['name', 'date_of_birth', 'gender', 'metadata'])
    users['user'] = demo_user
    if created:
        stdout.write(style.SUCCESS('Regular user created (user@example.com / user1234)'))
    else:
        stdout.write('Regular user already exists')

    client2, created = User.objects.get_or_create(
        email=DEMO_EMAILS['client2'],
        defaults={
            'is_staff': False,
            'name': 'Alex Rivera',
            'role': 'user',
            'date_of_birth': date(1988, 3, 22),
            'gender': 'female',
            'metadata': {'goal': 'maintenance'},
        },
    )
    _ensure_password(client2, 'client2123', created=created)
    users['client2'] = client2
    if created:
        stdout.write(style.SUCCESS('Second client created (client2@example.com / client2123)'))
    else:
        stdout.write('Second client already exists')

    return users
