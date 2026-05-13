import hashlib
import json
import os
import secrets
import uuid
from datetime import date
from decimal import Decimal, InvalidOperation

from django.conf import settings as django_settings
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.files.storage import default_storage
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from django.db import models as db_models

from auditlog.models import LogEntry

from .models import Intervention, MealEntry, MealPlan, SubscriptionPlan, UserMeal, UserSettings, Weight
from .tasks import (
    send_subscription_cancellation_email,
    send_subscription_confirmation_email,
    send_trial_started_email,
)


@login_required
@require_http_methods(['GET'])
def dashboard_home(request):
    return render(request, 'dashboard/home.html')

@login_required
@require_http_methods(['GET', 'POST'])
def profile(request):
    if request.method == 'POST':
        user = request.user
        user.name = request.POST.get('name', '')
        dob_str = request.POST.get('date_of_birth') or None
        dob = date.fromisoformat(dob_str) if dob_str else None
        user.date_of_birth = dob
        user.gender = request.POST.get('gender', '')
        if dob:
            today = date.today()
            user.metadata['age'] = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
        else:
            user.metadata.pop('age', None)
        user.save()
        messages.success(request, 'Profile updated successfully.')
        return redirect('dashboard:profile')
    return render(request, 'dashboard/profile.html')

@login_required
@require_http_methods(['GET', 'POST'])
def settings(request):
    user_settings, created = UserSettings.objects.get_or_create(user=request.user)

    if request.method == 'POST':
        user_settings.notify_comments = request.POST.get('comments') == 'on'
        user_settings.notify_updates = request.POST.get('updates') == 'on'
        user_settings.notify_marketing = request.POST.get('marketing') == 'on'
        user_settings.ollama_host = (request.POST.get('ollama_host') or '').strip()[:500]
        user_settings.ollama_model = (request.POST.get('ollama_model') or '').strip()[:200]
        reminder_raw = request.POST.get('weight_reminder_days', '5').strip()
        user_settings.weight_reminder_days = max(0, int(reminder_raw)) if reminder_raw.isdigit() else 5
        user_settings.save()

        messages.success(request, 'Settings updated successfully.')
        return redirect('dashboard:settings')

    # Check if a new API key was just generated (stored in session)
    new_api_key = request.session.pop('new_api_key', None)

    context = {
        'notification_settings': {
            'comments': user_settings.notify_comments,
            'updates': user_settings.notify_updates,
            'marketing': user_settings.notify_marketing,
        },
        'subscription': {
            'plan': user_settings.subscription_plan,
            'plan_name': user_settings.subscription_plan.name if user_settings.subscription_plan else None,
            'status': user_settings.subscription_status,
            'is_active': user_settings.is_subscription_active,
            'is_trial': user_settings.is_trial_active,
            'start_date': user_settings.subscription_start_date,
            'end_date': user_settings.subscription_end_date,
            'trial_end_date': user_settings.trial_end_date,
        },
        'api': {
            'has_key': bool(user_settings.api_key_hash),
            'key_prefix': user_settings.api_key_prefix,
            'key_created_at': user_settings.api_key_created_at,
            'new_key': new_api_key,
        },
        'ollama': {
            'host': user_settings.ollama_host,
            'model': user_settings.ollama_model,
            'effective_host': user_settings.get_effective_ollama_host(),
            'effective_model': user_settings.get_effective_ollama_model(),
            'default_host': django_settings.OLLAMA_HOST,
            'default_model': django_settings.OLLAMA_MODEL,
        },
        'weight_reminder_days': user_settings.weight_reminder_days,
    }
    return render(request, 'dashboard/settings.html', context)

@login_required
@require_http_methods(['POST'])
def generate_api_key(request):
    user_settings, created = UserSettings.objects.get_or_create(user=request.user)

    api_key = secrets.token_urlsafe(32)
    user_settings.api_key_hash = hashlib.sha256(api_key.encode()).hexdigest()
    user_settings.api_key_prefix = api_key[:8]
    user_settings.api_key_created_at = timezone.now()
    user_settings.save()

    # Store the key in session so it can be shown once on the settings page
    request.session['new_api_key'] = api_key

    messages.success(request, 'API key generated. Copy it now — it won\'t be shown again.')
    return redirect('dashboard:settings')

@login_required
@require_http_methods(['GET'])
def subscription_plans(request):
    plans = SubscriptionPlan.objects.filter(is_active=True)
    user_settings, created = UserSettings.objects.get_or_create(user=request.user)

    context = {
        'plans': plans,
        'current_plan': user_settings.subscription_plan,
        'subscription_status': user_settings.subscription_status,
        'is_subscription_active': user_settings.is_subscription_active,
        'is_trial_active': user_settings.is_trial_active,
    }
    return render(request, 'dashboard/subscription_plans.html', context)

@login_required
@require_http_methods(['POST'])
def subscribe_to_plan(request, plan_slug):
    plan = get_object_or_404(SubscriptionPlan, slug=plan_slug, is_active=True)
    user_settings = UserSettings.objects.get(user=request.user)

    # Check if user already has an active subscription
    if user_settings.is_subscription_active:
        messages.warning(request, 'You already have an active subscription.')
        return redirect('dashboard:subscription_plans')

    # Update user settings with new subscription
    user_settings.subscription_plan = plan
    user_settings.subscription_status = 'active'
    user_settings.subscription_start_date = timezone.now()

    # Set subscription end date based on interval
    if plan.interval == 'monthly':
        user_settings.subscription_end_date = timezone.now() + timezone.timedelta(days=30)
    else:  # yearly
        user_settings.subscription_end_date = timezone.now() + timezone.timedelta(days=365)

    user_settings.save()

    send_subscription_confirmation_email.enqueue(
        user_email=request.user.email,
        plan_name=plan.name,
    )

    messages.success(request, f'Successfully subscribed to {plan.name} plan.')
    return redirect('dashboard:settings')

@login_required
@require_http_methods(['POST'])
def cancel_subscription(request):
    user_settings = UserSettings.objects.get(user=request.user)

    if not user_settings.is_subscription_active:
        messages.warning(request, 'You do not have an active subscription to cancel.')
        return redirect('dashboard:settings')

    user_settings.subscription_status = 'cancelled'
    user_settings.save()

    send_subscription_cancellation_email.enqueue(user_email=request.user.email)

    messages.success(request, 'Your subscription has been cancelled.')
    return redirect('dashboard:settings')

@login_required
@require_http_methods(['POST'])
def start_trial(request):
    user_settings = UserSettings.objects.get(user=request.user)

    if user_settings.is_subscription_active or user_settings.is_trial_active:
        messages.warning(request, 'You already have an active subscription or trial.')
        return redirect('dashboard:subscription_plans')

    # Start trial period (14 days)
    user_settings.subscription_status = 'trial'
    user_settings.trial_end_date = timezone.now() + timezone.timedelta(days=14)
    user_settings.save()

    send_trial_started_email.enqueue(user_email=request.user.email)

    messages.success(request, 'Trial period started successfully.')
    return redirect('dashboard:settings')

ALLOWED_PIC_TYPES = {'image/jpeg', 'image/png', 'image/webp', 'image/gif'}
MAX_PIC_SIZE = 5 * 1024 * 1024  # 5 MB

@login_required
@require_http_methods(['POST'])
def upload_profile_pic(request):
    pic = request.FILES.get('profile_pic')
    if not pic:
        messages.error(request, 'No file selected.')
        return redirect('dashboard:profile')

    if pic.content_type not in ALLOWED_PIC_TYPES:
        messages.error(request, 'Only JPEG, PNG, WebP, and GIF images are allowed.')
        return redirect('dashboard:profile')

    if pic.size > MAX_PIC_SIZE:
        messages.error(request, 'Image must be under 5 MB.')
        return redirect('dashboard:profile')

    user = request.user
    ext = os.path.splitext(pic.name)[1].lower() or '.jpg'
    filename = f'profile_pics/{user.pk}/{uuid.uuid4().hex}{ext}'

    old_pic = user.metadata.get('profile_pic', '')
    if old_pic:
        old_path = old_pic.lstrip('/')
        if old_path.startswith(django_settings.MEDIA_URL):
            old_path = old_path[len(django_settings.MEDIA_URL):]
        if default_storage.exists(old_path):
            default_storage.delete(old_path)

    saved_path = default_storage.save(filename, pic)
    media_url = django_settings.MEDIA_URL if django_settings.MEDIA_URL.startswith('/') else f'/{django_settings.MEDIA_URL}'
    user.metadata['profile_pic'] = f'{media_url}{saved_path}'
    user.save(update_fields=['metadata'])

    messages.success(request, 'Profile picture updated.')
    return redirect('dashboard:profile')

@login_required
@require_http_methods(['POST'])
def remove_profile_pic(request):
    user = request.user
    old_pic = user.metadata.get('profile_pic', '')
    if old_pic:
        old_path = old_pic.lstrip('/')
        if old_path.startswith(django_settings.MEDIA_URL):
            old_path = old_path[len(django_settings.MEDIA_URL):]
        if default_storage.exists(old_path):
            default_storage.delete(old_path)
        user.metadata.pop('profile_pic', None)
        user.save(update_fields=['metadata'])
        messages.success(request, 'Profile picture removed.')
    return redirect('dashboard:profile')


# ---------------------------------------------------------------------------
# Weight CRUD — admin only
# ---------------------------------------------------------------------------

User = get_user_model()


def _parse_weight_form(request, *, forced_user=None):
    """Extract and validate weight form fields. Returns (data, errors).

    If forced_user is set (e.g. regular user logging own weight), that user is used
    and the POST ``user`` field is ignored.
    """
    errors = []
    user_id = request.POST.get('user')
    dt_str = request.POST.get('datetime', '').strip()
    value_str = request.POST.get('value', '').strip()
    source = request.POST.get('source', 'manual')
    metadata_str = request.POST.get('metadata', '').strip() or '{}'

    user_obj = None
    if forced_user is not None:
        user_obj = forced_user
    elif user_id:
        try:
            user_obj = User.objects.get(pk=user_id)
        except User.DoesNotExist:
            errors.append('Invalid user.')
    else:
        errors.append('User is required.')

    dt = None
    if dt_str:
        try:
            dt = timezone.datetime.fromisoformat(dt_str)
            if timezone.is_naive(dt):
                dt = timezone.make_aware(dt)
        except ValueError:
            errors.append('Invalid datetime format.')
    else:
        errors.append('Datetime is required.')

    value = None
    if value_str:
        try:
            value = Decimal(value_str)
            if value <= 0:
                errors.append('Weight must be positive.')
        except InvalidOperation:
            errors.append('Invalid weight value.')
    else:
        errors.append('Weight value is required.')

    meta = {}
    try:
        meta = json.loads(metadata_str)
        if not isinstance(meta, dict):
            errors.append('Metadata must be a JSON object.')
            meta = {}
    except json.JSONDecodeError:
        errors.append('Metadata is not valid JSON.')

    return {
        'user': user_obj,
        'datetime': dt,
        'value': value,
        'source': source,
        'metadata': meta,
    }, errors


@login_required
@require_http_methods(['GET'])
def weight_list(request):
    qs = Weight.objects.select_related('user')
    if request.user.is_staff:
        qs = qs.all()
        user_filter = request.GET.get('user')
        if user_filter:
            qs = qs.filter(user_id=user_filter)
    else:
        qs = qs.filter(user=request.user)
        user_filter = None

    source_filter = request.GET.get('source')
    if source_filter:
        qs = qs.filter(source=source_filter)

    paginator = Paginator(qs, 25)
    page = paginator.get_page(request.GET.get('page'))

    context = {
        'page': page,
        'users': User.objects.order_by('email') if request.user.is_staff else [],
        'sources': Weight.SOURCE_CHOICES,
        'current_user_filter': user_filter or '',
        'current_source_filter': source_filter or '',
    }
    return render(request, 'dashboard/weight_list.html', context)


@login_required
@require_http_methods(['GET'])
def weight_detail(request, pk):
    qs = Weight.objects.select_related('user')
    if not request.user.is_staff:
        qs = qs.filter(user=request.user)
    entry = get_object_or_404(qs, pk=pk)
    return render(request, 'dashboard/weight_detail.html', {'entry': entry})


@login_required
@require_http_methods(['GET', 'POST'])
def weight_create(request):
    forced_user = None if request.user.is_staff else request.user

    if request.method == 'POST':
        data, errors = _parse_weight_form(request, forced_user=forced_user)
        if errors:
            for e in errors:
                messages.error(request, e)
        else:
            Weight.objects.create(**data)
            messages.success(request, 'Weight entry created.')
            return redirect('dashboard:weight_list')

    context = {
        'users': User.objects.order_by('email') if request.user.is_staff else [],
        'sources': Weight.SOURCE_CHOICES,
    }
    return render(request, 'dashboard/weight_form.html', context)


@login_required
@require_http_methods(['GET', 'POST'])
def weight_edit(request, pk):
    qs = Weight.objects.all()
    if not request.user.is_staff:
        qs = qs.filter(user=request.user)
    entry = get_object_or_404(qs, pk=pk)

    forced_user = None if request.user.is_staff else request.user

    if request.method == 'POST':
        data, errors = _parse_weight_form(request, forced_user=forced_user)
        if errors:
            for e in errors:
                messages.error(request, e)
        else:
            for attr, val in data.items():
                setattr(entry, attr, val)
            entry.save()
            messages.success(request, 'Weight entry updated.')
            return redirect('dashboard:weight_detail', pk=entry.pk)

    context = {
        'entry': entry,
        'users': User.objects.order_by('email') if request.user.is_staff else [],
        'sources': Weight.SOURCE_CHOICES,
    }
    return render(request, 'dashboard/weight_form.html', context)


@login_required
@require_http_methods(['POST'])
def weight_delete(request, pk):
    qs = Weight.objects.all()
    if not request.user.is_staff:
        qs = qs.filter(user=request.user)
    entry = get_object_or_404(qs, pk=pk)
    entry.delete()
    messages.success(request, 'Weight entry deleted.')
    return redirect('dashboard:weight_list')


# ---------------------------------------------------------------------------
# User Management CRUD — admin only
# ---------------------------------------------------------------------------

GENDER_CHOICES = [
    ('', '— Not set —'),
    ('male', 'Male'),
    ('female', 'Female'),
    ('other', 'Other'),
    ('prefer_not_to_say', 'Prefer not to say'),
]

ROLE_CHOICES = User.ROLE_CHOICES


@staff_member_required
@require_http_methods(['GET'])
def user_list(request):
    qs = User.objects.all().order_by('-date_joined')

    q = request.GET.get('q', '').strip()
    if q:
        qs = qs.filter(
            db_models.Q(email__icontains=q) | db_models.Q(name__icontains=q)
        )

    status_filter = request.GET.get('status', '')
    if status_filter == 'active':
        qs = qs.filter(is_active=True)
    elif status_filter == 'inactive':
        qs = qs.filter(is_active=False)
    elif status_filter == 'staff':
        qs = qs.filter(is_staff=True)

    role_filter = request.GET.get('role', '')
    if role_filter in dict(ROLE_CHOICES):
        qs = qs.filter(role=role_filter)

    paginator = Paginator(qs, 25)
    page = paginator.get_page(request.GET.get('page'))

    context = {
        'page': page,
        'current_q': q,
        'current_status': status_filter,
        'current_role': role_filter,
        'role_choices': ROLE_CHOICES,
        'total_users': User.objects.count(),
    }
    return render(request, 'dashboard/user_list.html', context)


@staff_member_required
@require_http_methods(['GET'])
def user_detail(request, pk):
    managed_user = get_object_or_404(User, pk=pk)
    weight_entries = Weight.objects.filter(user=managed_user).order_by('-datetime')[:10]
    context = {
        'managed_user': managed_user,
        'weight_entries': weight_entries,
    }
    return render(request, 'dashboard/user_detail.html', context)


@staff_member_required
@require_http_methods(['GET', 'POST'])
def user_create(request):
    if request.method == 'POST':
        email = request.POST.get('email', '').strip()
        password = request.POST.get('password', '').strip()
        name = request.POST.get('name', '').strip()
        role = request.POST.get('role', 'user')
        dob_str = request.POST.get('date_of_birth', '').strip() or None
        gender = request.POST.get('gender', '')
        is_staff = request.POST.get('is_staff') == 'on'
        is_active = request.POST.get('is_active') == 'on'

        errors = []
        if not email:
            errors.append('Email is required.')
        elif User.objects.filter(email__iexact=email).exists():
            errors.append('A user with this email already exists.')
        if not password:
            errors.append('Password is required.')
        elif len(password) < 8:
            errors.append('Password must be at least 8 characters.')
        if role not in dict(ROLE_CHOICES):
            errors.append('Invalid role.')

        dob = None
        if dob_str:
            try:
                dob = date.fromisoformat(dob_str)
            except ValueError:
                errors.append('Invalid date of birth.')

        if errors:
            for e in errors:
                messages.error(request, e)
            context = {
                'gender_choices': GENDER_CHOICES,
                'role_choices': ROLE_CHOICES,
                'form_data': request.POST,
                'coach_speciality': request.POST.get('speciality', ''),
                'coach_years_of_experience': request.POST.get('years_of_experience', ''),
            }
            return render(request, 'dashboard/user_form.html', context)

        metadata = {}
        if role == 'coach':
            metadata['speciality'] = request.POST.get('speciality', '').strip()
            yoe = request.POST.get('years_of_experience', '').strip()
            metadata['years_of_experience'] = int(yoe) if yoe.isdigit() else None

        new_user = User.objects.create_user(
            email=email,
            password=password,
            name=name,
            role=role,
            date_of_birth=dob,
            gender=gender,
            metadata=metadata,
            is_staff=is_staff,
            is_active=is_active,
        )
        messages.success(request, f'User {new_user.email} created.')
        return redirect('dashboard:user_detail', pk=new_user.pk)

    context = {
        'gender_choices': GENDER_CHOICES,
        'role_choices': ROLE_CHOICES,
        'coach_speciality': '',
        'coach_years_of_experience': '',
    }
    return render(request, 'dashboard/user_form.html', context)


@staff_member_required
@require_http_methods(['GET', 'POST'])
def user_edit(request, pk):
    managed_user = get_object_or_404(User, pk=pk)

    if request.method == 'POST':
        email = request.POST.get('email', '').strip()
        name = request.POST.get('name', '').strip()
        role = request.POST.get('role', 'user')
        dob_str = request.POST.get('date_of_birth', '').strip() or None
        gender = request.POST.get('gender', '')
        is_staff = request.POST.get('is_staff') == 'on'
        is_active = request.POST.get('is_active') == 'on'
        new_password = request.POST.get('password', '').strip()

        errors = []
        if not email:
            errors.append('Email is required.')
        elif User.objects.filter(email__iexact=email).exclude(pk=pk).exists():
            errors.append('A user with this email already exists.')

        if new_password and len(new_password) < 8:
            errors.append('Password must be at least 8 characters.')
        if role not in dict(ROLE_CHOICES):
            errors.append('Invalid role.')

        dob = None
        if dob_str:
            try:
                dob = date.fromisoformat(dob_str)
            except ValueError:
                errors.append('Invalid date of birth.')

        if errors:
            for e in errors:
                messages.error(request, e)
            context = {
                'managed_user': managed_user,
                'gender_choices': GENDER_CHOICES,
                'role_choices': ROLE_CHOICES,
                'form_data': request.POST,
                'coach_speciality': request.POST.get('speciality', ''),
                'coach_years_of_experience': request.POST.get('years_of_experience', ''),
            }
            return render(request, 'dashboard/user_form.html', context)

        managed_user.email = email
        managed_user.name = name
        managed_user.role = role
        managed_user.date_of_birth = dob
        managed_user.gender = gender
        managed_user.is_staff = is_staff
        managed_user.is_active = is_active
        if new_password:
            managed_user.set_password(new_password)

        if role == 'coach':
            managed_user.metadata['speciality'] = request.POST.get('speciality', '').strip()
            yoe = request.POST.get('years_of_experience', '').strip()
            managed_user.metadata['years_of_experience'] = int(yoe) if yoe.isdigit() else None
        else:
            managed_user.metadata.pop('speciality', None)
            managed_user.metadata.pop('years_of_experience', None)

        managed_user.save()

        messages.success(request, f'User {managed_user.email} updated.')
        return redirect('dashboard:user_detail', pk=managed_user.pk)

    context = {
        'managed_user': managed_user,
        'gender_choices': GENDER_CHOICES,
        'role_choices': ROLE_CHOICES,
        'coach_speciality': managed_user.metadata.get('speciality', ''),
        'coach_years_of_experience': managed_user.metadata.get('years_of_experience', ''),
    }
    return render(request, 'dashboard/user_form.html', context)


@staff_member_required
@require_http_methods(['POST'])
def user_delete(request, pk):
    managed_user = get_object_or_404(User, pk=pk)
    if managed_user.pk == request.user.pk:
        messages.error(request, 'You cannot delete your own account.')
        return redirect('dashboard:user_detail', pk=pk)
    email = managed_user.email
    managed_user.delete()
    messages.success(request, f'User {email} deleted.')
    return redirect('dashboard:user_list')


# ---------------------------------------------------------------------------
# Meal Plan CRUD — admin only
# ---------------------------------------------------------------------------

def _parse_meal_plan_form(request):
    """Extract and validate meal plan form fields. Returns (data, errors)."""
    errors = []
    user_id = request.POST.get('user')
    title = request.POST.get('title', '').strip()
    start_date_str = request.POST.get('start_date', '').strip()
    end_date_str = request.POST.get('end_date', '').strip()
    goal = request.POST.get('goal', '').strip()
    notes = request.POST.get('notes', '').strip()
    dietary_preference = request.POST.get('dietary_preference', 'none')
    daily_cal = request.POST.get('daily_calorie_target', '').strip()
    daily_protein = request.POST.get('daily_protein_target', '').strip()
    daily_carbs = request.POST.get('daily_carbs_target', '').strip()
    daily_fat = request.POST.get('daily_fat_target', '').strip()
    daily_water = request.POST.get('daily_water_target_ml', '').strip()
    allergies_str = request.POST.get('allergies_restrictions', '').strip()
    supplements_str = request.POST.get('supplements', '').strip()

    user_obj = None
    if user_id:
        try:
            user_obj = User.objects.get(pk=user_id)
        except User.DoesNotExist:
            errors.append('Invalid user.')
    else:
        errors.append('User is required.')

    if not title:
        errors.append('Title is required.')

    start_date = None
    if start_date_str:
        try:
            start_date = date.fromisoformat(start_date_str)
        except ValueError:
            errors.append('Invalid start date.')
    else:
        errors.append('Start date is required.')

    end_date = None
    if end_date_str:
        try:
            end_date = date.fromisoformat(end_date_str)
        except ValueError:
            errors.append('Invalid end date.')
    else:
        errors.append('End date is required.')

    if start_date and end_date and end_date < start_date:
        errors.append('End date must be on or after start date.')

    if dietary_preference not in dict(MealPlan.DIETARY_CHOICES):
        dietary_preference = 'none'

    allergies = [a.strip() for a in allergies_str.split(',') if a.strip()] if allergies_str else []
    supps = [s.strip() for s in supplements_str.split(',') if s.strip()] if supplements_str else []

    data = {
        'user': user_obj,
        'title': title,
        'start_date': start_date,
        'end_date': end_date,
        'goal': goal,
        'notes': notes,
        'dietary_preference': dietary_preference,
        'allergies_restrictions': allergies,
        'supplements': supps,
        'daily_calorie_target': int(daily_cal) if daily_cal else None,
        'daily_protein_target': Decimal(daily_protein) if daily_protein else None,
        'daily_carbs_target': Decimal(daily_carbs) if daily_carbs else None,
        'daily_fat_target': Decimal(daily_fat) if daily_fat else None,
        'daily_water_target_ml': int(daily_water) if daily_water else None,
    }

    return data, errors


def _parse_inline_entries(request):
    """Parse repeatable meal entry rows from POST data. Returns list of dicts."""
    entries = []
    idx = 0
    while True:
        prefix = f'entry-{idx}-'
        title = request.POST.get(f'{prefix}title', '').strip()
        if not title and not request.POST.get(f'{prefix}meal_type'):
            break
        if not title:
            idx += 1
            continue

        entry_id = request.POST.get(f'{prefix}id', '').strip()
        meal_type = request.POST.get(f'{prefix}meal_type', 'breakfast')
        day_str = request.POST.get(f'{prefix}day_number', '1').strip()
        time_str = request.POST.get(f'{prefix}scheduled_time', '').strip()
        cal_str = request.POST.get(f'{prefix}calories', '0').strip()
        protein_str = request.POST.get(f'{prefix}protein', '0').strip()
        carbs_str = request.POST.get(f'{prefix}carbs', '0').strip()
        fat_str = request.POST.get(f'{prefix}fat', '0').strip()
        portion_notes = request.POST.get(f'{prefix}portion_notes', '').strip()

        scheduled_time = None
        if time_str:
            try:
                from datetime import time as dt_time
                parts = time_str.split(':')
                scheduled_time = dt_time(int(parts[0]), int(parts[1]))
            except (ValueError, IndexError):
                pass

        entries.append({
            'id': int(entry_id) if entry_id else None,
            'meal_type': meal_type if meal_type in dict(MealEntry.MEAL_TYPE_CHOICES) else 'breakfast',
            'day_number': max(1, int(day_str)) if day_str.isdigit() else 1,
            'scheduled_time': scheduled_time,
            'title': title,
            'calories': int(cal_str) if cal_str else 0,
            'protein': Decimal(protein_str) if protein_str else Decimal('0'),
            'carbs': Decimal(carbs_str) if carbs_str else Decimal('0'),
            'fat': Decimal(fat_str) if fat_str else Decimal('0'),
            'portion_notes': portion_notes,
            'sort_order': idx,
        })
        idx += 1
    return entries


def _save_inline_entries(meal, entries_data):
    """Create/update/delete entries for a meal plan based on inline form data."""
    existing_ids = set(meal.entries.values_list('id', flat=True))
    submitted_ids = {e['id'] for e in entries_data if e['id']}

    meal.entries.filter(id__in=existing_ids - submitted_ids).delete()

    for edata in entries_data:
        eid = edata.pop('id')
        if eid and eid in existing_ids:
            meal.entries.filter(id=eid).update(**edata)
        else:
            MealEntry.objects.create(meal_plan=meal, **edata)


def _meal_plan_form_context(meal=None):
    entries = []
    if meal:
        entries = list(meal.entries.order_by('day_number', 'sort_order').values(
            'id', 'meal_type', 'day_number', 'scheduled_time', 'title',
            'calories', 'protein', 'carbs', 'fat', 'portion_notes',
        ))
        for e in entries:
            if e['scheduled_time']:
                e['scheduled_time'] = e['scheduled_time'].strftime('%H:%M')
            else:
                e['scheduled_time'] = ''
            e['protein'] = str(e['protein'])
            e['carbs'] = str(e['carbs'])
            e['fat'] = str(e['fat'])
    return {
        'meal': meal,
        'users': User.objects.order_by('email'),
        'dietary_choices': MealPlan.DIETARY_CHOICES,
        'meal_types': MealEntry.MEAL_TYPE_CHOICES,
        'existing_entries': entries,
    }


@staff_member_required
@require_http_methods(['GET'])
def meal_list(request):
    qs = MealPlan.objects.select_related('user').prefetch_related('entries').all()

    user_filter = request.GET.get('user')
    if user_filter:
        qs = qs.filter(user_id=user_filter)

    diet_filter = request.GET.get('dietary_preference')
    if diet_filter:
        qs = qs.filter(dietary_preference=diet_filter)

    date_from = request.GET.get('date_from')
    if date_from:
        try:
            qs = qs.filter(start_date__gte=date.fromisoformat(date_from))
        except ValueError:
            pass

    date_to = request.GET.get('date_to')
    if date_to:
        try:
            qs = qs.filter(end_date__lte=date.fromisoformat(date_to))
        except ValueError:
            pass

    paginator = Paginator(qs, 25)
    page = paginator.get_page(request.GET.get('page'))

    context = {
        'page': page,
        'users': User.objects.order_by('email'),
        'dietary_choices': MealPlan.DIETARY_CHOICES,
        'current_user_filter': user_filter or '',
        'current_diet_filter': diet_filter or '',
        'current_date_from': date_from or '',
        'current_date_to': date_to or '',
    }
    return render(request, 'dashboard/meal_list.html', context)


@staff_member_required
@require_http_methods(['GET'])
def meal_detail(request, pk):
    meal = get_object_or_404(MealPlan.objects.select_related('user'), pk=pk)
    entries = meal.entries.select_related('actual_meal').order_by('day_number', 'sort_order')
    days = {}
    for entry in entries:
        days.setdefault(entry.day_number, []).append(entry)
    context = {
        'meal': meal,
        'grouped_entries': sorted(days.items()),
        'entry_count': entries.count(),
    }
    return render(request, 'dashboard/meal_detail.html', context)


@staff_member_required
@require_http_methods(['GET', 'POST'])
def meal_create(request):
    if request.method == 'POST':
        data, errors = _parse_meal_plan_form(request)
        if errors:
            for e in errors:
                messages.error(request, e)
        else:
            plan = MealPlan.objects.create(**data)
            entries_data = _parse_inline_entries(request)
            _save_inline_entries(plan, entries_data)
            messages.success(request, 'Meal plan created.')
            return redirect('dashboard:meal_detail', pk=plan.pk)

    return render(request, 'dashboard/meal_form.html', _meal_plan_form_context())


@staff_member_required
@require_http_methods(['GET', 'POST'])
def meal_edit(request, pk):
    meal = get_object_or_404(MealPlan, pk=pk)

    if request.method == 'POST':
        data, errors = _parse_meal_plan_form(request)
        if errors:
            for e in errors:
                messages.error(request, e)
        else:
            for attr, val in data.items():
                setattr(meal, attr, val)
            meal.save()
            entries_data = _parse_inline_entries(request)
            _save_inline_entries(meal, entries_data)
            messages.success(request, 'Meal plan updated.')
            return redirect('dashboard:meal_detail', pk=meal.pk)

    return render(request, 'dashboard/meal_form.html', _meal_plan_form_context(meal))


@staff_member_required
@require_http_methods(['POST'])
def meal_delete(request, pk):
    meal = get_object_or_404(MealPlan, pk=pk)
    meal.delete()
    messages.success(request, 'Meal plan deleted.')
    return redirect('dashboard:meal_list')


# ---------------------------------------------------------------------------
# Meal Entry CRUD — admin only (entries within a meal plan)
# ---------------------------------------------------------------------------

def _parse_entry_form(request):
    """Extract and validate meal entry form fields."""
    errors = []
    meal_type = request.POST.get('meal_type', '')
    day_str = request.POST.get('day_number', '').strip()
    time_str = request.POST.get('scheduled_time', '').strip()
    title = request.POST.get('title', '').strip()
    foods_str = request.POST.get('foods_json', '').strip() or '[]'
    cal_str = request.POST.get('calories', '').strip() or '0'
    protein_str = request.POST.get('protein', '').strip() or '0'
    carbs_str = request.POST.get('carbs', '').strip() or '0'
    fat_str = request.POST.get('fat', '').strip() or '0'
    portion_notes = request.POST.get('portion_notes', '').strip()
    subs_str = request.POST.get('substitutions', '').strip() or '[]'
    sort_str = request.POST.get('sort_order', '').strip() or '0'

    if not title:
        errors.append('Title is required.')
    if meal_type not in dict(MealEntry.MEAL_TYPE_CHOICES):
        errors.append('Invalid meal type.')

    day_number = 1
    if day_str:
        try:
            day_number = int(day_str)
            if day_number < 1:
                errors.append('Day number must be at least 1.')
        except ValueError:
            errors.append('Invalid day number.')
    else:
        errors.append('Day number is required.')

    scheduled_time = None
    if time_str:
        try:
            from datetime import time as dt_time
            parts = time_str.split(':')
            scheduled_time = dt_time(int(parts[0]), int(parts[1]))
        except (ValueError, IndexError):
            errors.append('Invalid time format (use HH:MM).')

    foods = []
    try:
        foods = json.loads(foods_str)
        if not isinstance(foods, list):
            errors.append('Foods must be a JSON array.')
            foods = []
    except json.JSONDecodeError:
        errors.append('Foods JSON is invalid.')

    subs = []
    try:
        subs = json.loads(subs_str)
        if not isinstance(subs, list):
            errors.append('Substitutions must be a JSON array.')
            subs = []
    except json.JSONDecodeError:
        errors.append('Substitutions JSON is invalid.')

    try:
        calories = int(cal_str)
    except ValueError:
        errors.append('Calories must be a whole number.')
        calories = 0

    try:
        protein = Decimal(protein_str)
    except InvalidOperation:
        errors.append('Invalid protein value.')
        protein = Decimal('0')

    try:
        carbs = Decimal(carbs_str)
    except InvalidOperation:
        errors.append('Invalid carbs value.')
        carbs = Decimal('0')

    try:
        fat = Decimal(fat_str)
    except InvalidOperation:
        errors.append('Invalid fat value.')
        fat = Decimal('0')

    try:
        sort_order = int(sort_str)
    except ValueError:
        sort_order = 0

    return {
        'meal_type': meal_type,
        'day_number': day_number,
        'scheduled_time': scheduled_time,
        'title': title,
        'foods_json': foods,
        'calories': calories,
        'protein': protein,
        'carbs': carbs,
        'fat': fat,
        'portion_notes': portion_notes,
        'substitutions': subs,
        'sort_order': sort_order,
    }, errors


@staff_member_required
@require_http_methods(['GET', 'POST'])
def entry_create(request, meal_pk):
    meal = get_object_or_404(MealPlan.objects.select_related('user'), pk=meal_pk)

    if request.method == 'POST':
        data, errors = _parse_entry_form(request)
        if errors:
            for e in errors:
                messages.error(request, e)
        else:
            MealEntry.objects.create(meal_plan=meal, **data)
            messages.success(request, 'Meal entry added.')
            return redirect('dashboard:meal_detail', pk=meal.pk)

    context = {
        'meal': meal,
        'meal_types': MealEntry.MEAL_TYPE_CHOICES,
    }
    return render(request, 'dashboard/entry_form.html', context)


@staff_member_required
@require_http_methods(['GET', 'POST'])
def entry_edit(request, pk):
    entry = get_object_or_404(MealEntry.objects.select_related('meal_plan', 'meal_plan__user'), pk=pk)

    if request.method == 'POST':
        data, errors = _parse_entry_form(request)
        if errors:
            for e in errors:
                messages.error(request, e)
        else:
            for attr, val in data.items():
                setattr(entry, attr, val)
            entry.save()
            messages.success(request, 'Meal entry updated.')
            return redirect('dashboard:meal_detail', pk=entry.meal_plan_id)

    context = {
        'meal': entry.meal_plan,
        'entry': entry,
        'meal_types': MealEntry.MEAL_TYPE_CHOICES,
    }
    return render(request, 'dashboard/entry_form.html', context)


@staff_member_required
@require_http_methods(['POST'])
def entry_delete(request, pk):
    entry = get_object_or_404(MealEntry, pk=pk)
    meal_pk = entry.meal_plan_id
    entry.delete()
    messages.success(request, 'Meal entry deleted.')
    return redirect('dashboard:meal_detail', pk=meal_pk)


# ---------------------------------------------------------------------------
# User Meal CRUD — staff see all users; regular users see only their own meals
# ---------------------------------------------------------------------------

def _parse_usermeal_form(request, *, forced_user=None):
    """Extract and validate user meal form fields. Returns (data, errors).

    When forced_user is set, that user is used and the POST ``user`` field is ignored.
    """
    errors = []
    user_id = request.POST.get('user')
    meal_type = request.POST.get('meal_type', '')
    title = request.POST.get('title', '').strip()
    time_str = request.POST.get('time_taken', '').strip()
    description = request.POST.get('description', '').strip()
    calories_str = request.POST.get('calories', '').strip() or '0'
    metadata_str = request.POST.get('metadata', '').strip() or '{}'

    user_obj = None
    if forced_user is not None:
        user_obj = forced_user
    elif user_id:
        try:
            user_obj = User.objects.get(pk=user_id)
        except User.DoesNotExist:
            errors.append('Invalid user.')
    else:
        errors.append('User is required.')

    if not title:
        errors.append('Title is required.')

    if meal_type not in dict(UserMeal.MEAL_TYPE_CHOICES):
        errors.append('Invalid meal type.')

    time_taken = None
    if time_str:
        try:
            time_taken = timezone.datetime.fromisoformat(time_str)
            if timezone.is_naive(time_taken):
                time_taken = timezone.make_aware(time_taken)
        except ValueError:
            errors.append('Invalid datetime format.')
    else:
        errors.append('Time taken is required.')

    try:
        calories = int(calories_str)
    except ValueError:
        errors.append('Calories must be a whole number.')
        calories = 0

    meta = {}
    try:
        meta = json.loads(metadata_str)
        if not isinstance(meta, dict):
            errors.append('Metadata must be a JSON object.')
            meta = {}
    except json.JSONDecodeError:
        errors.append('Metadata is not valid JSON.')

    return {
        'user': user_obj,
        'meal_type': meal_type,
        'title': title,
        'time_taken': time_taken,
        'description': description,
        'calories': calories,
        'metadata': meta,
    }, errors


@login_required
@require_http_methods(['GET'])
def usermeal_list(request):
    qs = UserMeal.objects.select_related('user')
    if request.user.is_staff:
        qs = qs.all()
        user_filter = request.GET.get('user')
        if user_filter:
            qs = qs.filter(user_id=user_filter)
    else:
        qs = qs.filter(user=request.user)
        user_filter = None

    type_filter = request.GET.get('meal_type')
    if type_filter:
        qs = qs.filter(meal_type=type_filter)

    paginator = Paginator(qs, 25)
    page = paginator.get_page(request.GET.get('page'))

    context = {
        'page': page,
        'users': User.objects.order_by('email') if request.user.is_staff else [],
        'meal_types': UserMeal.MEAL_TYPE_CHOICES,
        'current_user_filter': user_filter or '',
        'current_type_filter': type_filter or '',
    }
    return render(request, 'dashboard/usermeal_list.html', context)


@login_required
@require_http_methods(['GET'])
def usermeal_detail(request, pk):
    qs = UserMeal.objects.select_related('user')
    if not request.user.is_staff:
        qs = qs.filter(user=request.user)
    entry = get_object_or_404(qs, pk=pk)
    return render(request, 'dashboard/usermeal_detail.html', {'entry': entry})


@login_required
@require_http_methods(['GET', 'POST'])
def usermeal_create(request):
    forced_user = None if request.user.is_staff else request.user

    if request.method == 'POST':
        data, errors = _parse_usermeal_form(request, forced_user=forced_user)
        if errors:
            for e in errors:
                messages.error(request, e)
        else:
            UserMeal.objects.create(**data)
            messages.success(request, 'User meal recorded.')
            return redirect('dashboard:usermeal_list')

    context = {
        'users': User.objects.order_by('email') if request.user.is_staff else [],
        'meal_types': UserMeal.MEAL_TYPE_CHOICES,
    }
    return render(request, 'dashboard/usermeal_form.html', context)


@login_required
@require_http_methods(['GET', 'POST'])
def usermeal_edit(request, pk):
    qs = UserMeal.objects.all()
    if not request.user.is_staff:
        qs = qs.filter(user=request.user)
    entry = get_object_or_404(qs, pk=pk)

    forced_user = None if request.user.is_staff else request.user

    if request.method == 'POST':
        data, errors = _parse_usermeal_form(request, forced_user=forced_user)
        if errors:
            for e in errors:
                messages.error(request, e)
        else:
            for attr, val in data.items():
                setattr(entry, attr, val)
            entry.save()
            messages.success(request, 'User meal updated.')
            return redirect('dashboard:usermeal_detail', pk=entry.pk)

    context = {
        'entry': entry,
        'users': User.objects.order_by('email') if request.user.is_staff else [],
        'meal_types': UserMeal.MEAL_TYPE_CHOICES,
    }
    return render(request, 'dashboard/usermeal_form.html', context)


@login_required
@require_http_methods(['POST'])
def usermeal_delete(request, pk):
    qs = UserMeal.objects.all()
    if not request.user.is_staff:
        qs = qs.filter(user=request.user)
    entry = get_object_or_404(qs, pk=pk)
    entry.delete()
    messages.success(request, 'User meal deleted.')
    return redirect('dashboard:usermeal_list')


# ---------------------------------------------------------------------------
# Intervention CRUD — admin only
# ---------------------------------------------------------------------------

def _parse_intervention_form(request):
    """Extract and validate intervention form fields. Returns (data, errors)."""
    errors = []
    user_id = request.POST.get('user')
    int_type = request.POST.get('type', '')
    status = request.POST.get('status', 'pending')
    priority = request.POST.get('priority', 'normal')
    title = request.POST.get('title', '').strip()
    description = request.POST.get('description', '').strip()
    trigger_source = request.POST.get('trigger_source', '').strip()
    target_metric = request.POST.get('target_metric', '').strip()
    target_value_str = request.POST.get('target_value', '').strip()
    current_value_str = request.POST.get('current_value', '').strip()
    action_str = request.POST.get('action_json', '').strip() or '{}'
    scheduled_str = request.POST.get('scheduled_at', '').strip()
    completed_str = request.POST.get('completed_at', '').strip()
    created_by = request.POST.get('created_by', '').strip()

    user_obj = None
    if user_id:
        try:
            user_obj = User.objects.get(pk=user_id)
        except User.DoesNotExist:
            errors.append('Invalid user.')
    else:
        errors.append('User is required.')

    if not title:
        errors.append('Title is required.')

    if int_type not in dict(Intervention.TYPE_CHOICES):
        errors.append('Invalid intervention type.')
    if status not in dict(Intervention.STATUS_CHOICES):
        errors.append('Invalid status.')
    if priority not in dict(Intervention.PRIORITY_CHOICES):
        errors.append('Invalid priority.')

    target_value = None
    if target_value_str:
        try:
            target_value = Decimal(target_value_str)
        except InvalidOperation:
            errors.append('Invalid target value.')

    current_value = None
    if current_value_str:
        try:
            current_value = Decimal(current_value_str)
        except InvalidOperation:
            errors.append('Invalid current value.')

    action_json = {}
    try:
        action_json = json.loads(action_str)
        if not isinstance(action_json, dict):
            errors.append('Action JSON must be an object.')
            action_json = {}
    except json.JSONDecodeError:
        errors.append('Action JSON is invalid.')

    scheduled_at = None
    if scheduled_str:
        try:
            scheduled_at = timezone.datetime.fromisoformat(scheduled_str)
            if timezone.is_naive(scheduled_at):
                scheduled_at = timezone.make_aware(scheduled_at)
        except ValueError:
            errors.append('Invalid scheduled datetime.')

    completed_at = None
    if completed_str:
        try:
            completed_at = timezone.datetime.fromisoformat(completed_str)
            if timezone.is_naive(completed_at):
                completed_at = timezone.make_aware(completed_at)
        except ValueError:
            errors.append('Invalid completed datetime.')

    return {
        'user': user_obj,
        'type': int_type,
        'status': status,
        'priority': priority,
        'title': title,
        'description': description,
        'trigger_source': trigger_source,
        'target_metric': target_metric,
        'target_value': target_value,
        'current_value': current_value,
        'action_json': action_json,
        'scheduled_at': scheduled_at,
        'completed_at': completed_at,
        'created_by': created_by,
    }, errors


@staff_member_required
@require_http_methods(['GET'])
def intervention_list(request):
    qs = Intervention.objects.select_related('user').all()

    user_filter = request.GET.get('user')
    if user_filter:
        qs = qs.filter(user_id=user_filter)

    type_filter = request.GET.get('type')
    if type_filter:
        qs = qs.filter(type=type_filter)

    status_filter = request.GET.get('status')
    if status_filter:
        qs = qs.filter(status=status_filter)

    paginator = Paginator(qs, 25)
    page = paginator.get_page(request.GET.get('page'))

    context = {
        'page': page,
        'users': User.objects.order_by('email'),
        'types': Intervention.TYPE_CHOICES,
        'statuses': Intervention.STATUS_CHOICES,
        'current_user_filter': user_filter or '',
        'current_type_filter': type_filter or '',
        'current_status_filter': status_filter or '',
    }
    return render(request, 'dashboard/intervention_list.html', context)


@staff_member_required
@require_http_methods(['GET'])
def intervention_detail(request, pk):
    entry = get_object_or_404(Intervention.objects.select_related('user'), pk=pk)
    return render(request, 'dashboard/intervention_detail.html', {'entry': entry})


@staff_member_required
@require_http_methods(['GET', 'POST'])
def intervention_create(request):
    if request.method == 'POST':
        data, errors = _parse_intervention_form(request)
        if errors:
            for e in errors:
                messages.error(request, e)
        else:
            Intervention.objects.create(**data)
            messages.success(request, 'Intervention created.')
            return redirect('dashboard:intervention_list')

    context = {
        'users': User.objects.order_by('email'),
        'types': Intervention.TYPE_CHOICES,
        'statuses': Intervention.STATUS_CHOICES,
        'priorities': Intervention.PRIORITY_CHOICES,
    }
    return render(request, 'dashboard/intervention_form.html', context)


@staff_member_required
@require_http_methods(['GET', 'POST'])
def intervention_edit(request, pk):
    entry = get_object_or_404(Intervention, pk=pk)

    if request.method == 'POST':
        data, errors = _parse_intervention_form(request)
        if errors:
            for e in errors:
                messages.error(request, e)
        else:
            for attr, val in data.items():
                setattr(entry, attr, val)
            entry.save()
            messages.success(request, 'Intervention updated.')
            return redirect('dashboard:intervention_detail', pk=entry.pk)

    context = {
        'entry': entry,
        'users': User.objects.order_by('email'),
        'types': Intervention.TYPE_CHOICES,
        'statuses': Intervention.STATUS_CHOICES,
        'priorities': Intervention.PRIORITY_CHOICES,
    }
    return render(request, 'dashboard/intervention_form.html', context)


@staff_member_required
@require_http_methods(['POST'])
def intervention_delete(request, pk):
    entry = get_object_or_404(Intervention, pk=pk)
    entry.delete()
    messages.success(request, 'Intervention deleted.')
    return redirect('dashboard:intervention_list')


# ---------------------------------------------------------------------------
# Audit Logs — admin only
# ---------------------------------------------------------------------------

ACTION_LABELS = {
    LogEntry.Action.CREATE: 'Create',
    LogEntry.Action.UPDATE: 'Update',
    LogEntry.Action.DELETE: 'Delete',
    LogEntry.Action.ACCESS: 'Access',
}


@staff_member_required
@require_http_methods(['GET'])
def audit_log_list(request):
    qs = LogEntry.objects.select_related('content_type', 'actor').order_by('-timestamp')

    action_filter = request.GET.get('action', '')
    if action_filter.isdigit():
        qs = qs.filter(action=int(action_filter))

    user_filter = request.GET.get('user', '')
    if user_filter:
        qs = qs.filter(actor_id=user_filter)

    model_filter = request.GET.get('model', '')
    if model_filter:
        qs = qs.filter(content_type_id=model_filter)

    paginator = Paginator(qs, 30)
    page = paginator.get_page(request.GET.get('page'))

    from django.contrib.contenttypes.models import ContentType
    tracked_cts = (
        ContentType.objects
        .filter(logentry__isnull=False)
        .distinct()
        .order_by('model')
    )

    context = {
        'page': page,
        'users': User.objects.filter(is_staff=True).order_by('email'),
        'actions': [(k, v) for k, v in ACTION_LABELS.items()],
        'content_types': tracked_cts,
        'current_action_filter': action_filter,
        'current_user_filter': user_filter,
        'current_model_filter': model_filter,
        'action_labels': ACTION_LABELS,
    }
    return render(request, 'dashboard/audit_log_list.html', context)
