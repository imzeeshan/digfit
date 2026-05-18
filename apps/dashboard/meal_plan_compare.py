"""Meal plan vs logged meals — shared context, plan resolution, and DB comparison."""

from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal
from typing import Any

from django.db.models import Count, Sum
from django.utils import timezone

from .models import MealEntry, MealPlan, UserMeal


def _json_safe(value: Any) -> Any:
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (list, tuple)):
        return [_json_safe(v) for v in value]
    if isinstance(value, dict):
        return {k: _json_safe(v) for k, v in value.items()}
    return value


def _macro_totals(entries) -> dict[str, float]:
    agg = entries.aggregate(
        calories=Sum('calories'),
        protein=Sum('protein'),
        carbs=Sum('carbs'),
        fat=Sum('fat'),
    )
    return {
        'calories': int(agg['calories'] or 0),
        'protein_g': _json_safe(agg['protein'] or 0),
        'carbs_g': _json_safe(agg['carbs'] or 0),
        'fat_g': _json_safe(agg['fat'] or 0),
    }


def plan_date_for_day(plan: MealPlan, day_number: int) -> date:
    return plan.start_date + timedelta(days=day_number - 1)


def build_meal_comparison_context(plan: MealPlan) -> dict[str, Any]:
    """Structured context (used by LLM compare and DB compare)."""
    user = plan.user
    entries: list[dict[str, Any]] = []
    for e in plan.entries.order_by('day_number', 'sort_order'):
        entries.append(
            {
                'day_number': e.day_number,
                'meal_type': e.meal_type,
                'meal_type_label': e.get_meal_type_display(),
                'title': e.title,
                'scheduled_time': e.scheduled_time.isoformat() if e.scheduled_time else None,
                'calories': e.calories,
                'protein_g': _json_safe(e.protein),
                'carbs_g': _json_safe(e.carbs),
                'fat_g': _json_safe(e.fat),
                'foods': e.foods_json or [],
                'portion_notes': e.portion_notes or '',
                'linked_actual_meal_id': e.actual_meal_id,
            }
        )

    actual_qs = UserMeal.objects.filter(
        user=user,
        time_taken__date__gte=plan.start_date,
        time_taken__date__lte=plan.end_date,
    ).order_by('time_taken')
    actual: list[dict[str, Any]] = []
    for m in actual_qs:
        actual.append(
            {
                'id': m.pk,
                'meal_type': m.meal_type,
                'meal_type_label': m.get_meal_type_display(),
                'title': m.title,
                'time_taken': m.time_taken.isoformat(),
                'calories': m.calories,
                'description': (m.description or '')[:500],
            }
        )

    agg = actual_qs.aggregate(total_kcal=Sum('calories'))
    actual_total_kcal = int(agg['total_kcal'] or 0)

    return {
        'meal_plan': {
            'id': plan.pk,
            'title': plan.title,
            'start_date': str(plan.start_date),
            'end_date': str(plan.end_date),
            'goal': plan.goal or '',
            'notes': (plan.notes or '')[:800],
            'dietary_preference': plan.dietary_preference,
            'daily_calorie_target': plan.daily_calorie_target,
            'daily_protein_target': _json_safe(plan.daily_protein_target)
            if plan.daily_protein_target is not None
            else None,
            'daily_carbs_target': _json_safe(plan.daily_carbs_target)
            if plan.daily_carbs_target is not None
            else None,
            'daily_fat_target': _json_safe(plan.daily_fat_target)
            if plan.daily_fat_target is not None
            else None,
            'planned_entries': entries,
            'planned_total_calories_sum': plan.total_calories,
        },
        'actual_meals_in_plan_window': actual,
        'stats': {
            'planned_entry_count': len(entries),
            'actual_meal_count': len(actual),
            'actual_total_calories_logged': actual_total_kcal,
            'planned_sum_calories_from_entries': plan.total_calories,
        },
    }


def resolve_meal_plan_for_user_comparison(user) -> tuple[MealPlan | None, str | None]:
    """Choose one plan for meal comparison (LLM or DB).

    Returns ``(plan, selection_reason)`` — see docstring in original implementation.
    """
    today = timezone.now().date()
    base = MealPlan.objects.filter(user=user).select_related('user')

    overlapping = (
        base.filter(start_date__lte=today, end_date__gte=today)
        .annotate(meal_entry_count=Count('entries', distinct=True))
        .order_by('-meal_entry_count', '-start_date')
    )
    best_overlap = overlapping.first()
    if best_overlap is not None:
        if best_overlap.meal_entry_count > 0:
            return best_overlap, 'active_window'
        filled = (
            base.annotate(meal_entry_count=Count('entries', distinct=True))
            .filter(meal_entry_count__gt=0)
            .order_by('-start_date')
            .first()
        )
        if filled is not None:
            return filled, 'fallback_latest_with_entries'
        return best_overlap, 'active_window'

    latest = (
        base.annotate(meal_entry_count=Count('entries', distinct=True))
        .order_by('-meal_entry_count', '-start_date')
        .first()
    )
    if latest is not None:
        return latest, 'latest_by_start_date'
    return None, None


def _match_actual_meal(
    entry: MealEntry,
    plan: MealPlan,
    meals_by_date_type: dict[tuple[date, str], list[UserMeal]],
    used_meal_ids: set[int],
) -> UserMeal | None:
    slot_date = plan_date_for_day(plan, entry.day_number)
    key = (slot_date, entry.meal_type)
    for meal in meals_by_date_type.get(key, []):
        if meal.pk not in used_meal_ids:
            return meal
    return None


def _build_insights(
    plan: MealPlan,
    *,
    planned_total: int,
    actual_total: int,
    linked_count: int,
    entry_count: int,
    missing_log_count: int,
    extra_count: int,
    daily_rows: list[dict],
) -> list[str]:
    insights: list[str] = []
    if entry_count == 0:
        insights.append(
            'This plan has no structured meal entries; compare logged meals to daily targets only.',
        )
    elif planned_total and actual_total:
        pct = round((actual_total - planned_total) / planned_total * 100)
        if pct > 10:
            insights.append(f'Logged calories are {pct}% above the sum of planned entries.')
        elif pct < -10:
            insights.append(f'Logged calories are {abs(pct)}% below the sum of planned entries.')
        else:
            insights.append('Total logged calories are within 10% of planned entry totals.')

    if entry_count:
        adherence = round(linked_count / entry_count * 100)
        insights.append(
            f'{linked_count} of {entry_count} planned slots are explicitly linked ({adherence}% adherence).',
        )
    if missing_log_count:
        insights.append(
            f'{missing_log_count} planned slot(s) have no matching log on the same day and meal type.',
        )
    if extra_count:
        insights.append(
            f'{extra_count} meal(s) were logged in the plan window but do not match an open planned slot.',
        )

    if plan.daily_calorie_target and daily_rows:
        over_days = sum(
            1
            for row in daily_rows
            if row.get('actual', {}).get('calories', 0) > plan.daily_calorie_target
        )
        under_days = sum(
            1
            for row in daily_rows
            if 0 < row.get('actual', {}).get('calories', 0) < plan.daily_calorie_target
        )
        if over_days:
            insights.append(f'{over_days} day(s) exceeded the daily calorie target.')
        if under_days:
            insights.append(f'{under_days} day(s) were under the daily calorie target.')

    return insights


def compare_meal_plan_db(plan: MealPlan) -> dict[str, Any]:
    """Deterministic plan vs UserMeal comparison (no LLM)."""
    entries_qs = plan.entries.select_related('actual_meal').order_by('day_number', 'sort_order')
    actual_qs = UserMeal.objects.filter(
        user=plan.user,
        time_taken__date__gte=plan.start_date,
        time_taken__date__lte=plan.end_date,
    ).order_by('time_taken')

    meals_by_date_type: dict[tuple[date, str], list[UserMeal]] = defaultdict(list)
    for meal in actual_qs:
        meals_by_date_type[(meal.time_taken.date(), meal.meal_type)].append(meal)

    used_meal_ids: set[int] = set()
    slots: list[dict[str, Any]] = []
    missing_log_count = 0
    matched_unlinked_count = 0
    linked_count = 0

    for entry in entries_qs:
        slot_date = plan_date_for_day(plan, entry.day_number)
        actual_meal = None
        status = 'missing_log'

        if entry.actual_meal_id:
            actual_meal = entry.actual_meal
            status = 'linked'
            linked_count += 1
            used_meal_ids.add(actual_meal.pk)
        else:
            candidate = _match_actual_meal(entry, plan, meals_by_date_type, used_meal_ids)
            if candidate:
                actual_meal = candidate
                status = 'matched_unlinked'
                matched_unlinked_count += 1
                used_meal_ids.add(candidate.pk)
            else:
                missing_log_count += 1

        slot: dict[str, Any] = {
            'entry_id': entry.pk,
            'day_number': entry.day_number,
            'date': str(slot_date),
            'meal_type': entry.meal_type,
            'meal_type_label': entry.get_meal_type_display(),
            'planned_title': entry.title,
            'planned_calories': entry.calories,
            'planned_protein_g': _json_safe(entry.protein),
            'planned_carbs_g': _json_safe(entry.carbs),
            'planned_fat_g': _json_safe(entry.fat),
            'status': status,
            'actual_meal_id': actual_meal.pk if actual_meal else None,
            'actual_title': actual_meal.title if actual_meal else None,
            'actual_calories': actual_meal.calories if actual_meal else None,
        }
        if actual_meal is not None:
            slot['calorie_delta'] = actual_meal.calories - entry.calories
        slots.append(slot)

    extra_meals = [
        {
            'id': m.pk,
            'meal_type': m.meal_type,
            'meal_type_label': m.get_meal_type_display(),
            'title': m.title,
            'time_taken': m.time_taken.isoformat(),
            'calories': m.calories,
        }
        for m in actual_qs
        if m.pk not in used_meal_ids
    ]

    planned_totals = _macro_totals(entries_qs)
    actual_totals = {
        'calories': int(actual_qs.aggregate(t=Sum('calories'))['t'] or 0),
    }

    daily: list[dict[str, Any]] = []
    duration = plan.duration_days or max((e.day_number for e in entries_qs), default=0)
    for day_num in range(1, duration + 1):
        day_date = plan_date_for_day(plan, day_num)
        if day_date > plan.end_date:
            break
        day_entries = entries_qs.filter(day_number=day_num)
        day_planned = _macro_totals(day_entries)
        day_actual_qs = actual_qs.filter(time_taken__date=day_date)
        day_actual_kcal = int(day_actual_qs.aggregate(t=Sum('calories'))['t'] or 0)
        row: dict[str, Any] = {
            'day_number': day_num,
            'date': str(day_date),
            'planned': {**day_planned, 'entry_count': day_entries.count()},
            'actual': {
                'calories': day_actual_kcal,
                'meal_count': day_actual_qs.count(),
            },
        }
        if day_planned['calories']:
            row['variance'] = {
                'calories_delta': day_actual_kcal - day_planned['calories'],
                'calories_pct': round(
                    (day_actual_kcal - day_planned['calories']) / day_planned['calories'] * 100,
                    1,
                ),
            }
        if plan.daily_calorie_target is not None:
            row['daily_calorie_target'] = plan.daily_calorie_target
            row['target_delta'] = day_actual_kcal - plan.daily_calorie_target
        daily.append(row)

    by_type: list[dict[str, Any]] = []
    for meal_type, label in MealEntry.MEAL_TYPE_CHOICES:
        type_entries = entries_qs.filter(meal_type=meal_type)
        type_actual = actual_qs.filter(meal_type=meal_type)
        if not type_entries.exists() and not type_actual.exists():
            continue
        planned_kcal = int(type_entries.aggregate(t=Sum('calories'))['t'] or 0)
        actual_kcal = int(type_actual.aggregate(t=Sum('calories'))['t'] or 0)
        by_type.append(
            {
                'meal_type': meal_type,
                'meal_type_label': label,
                'planned_count': type_entries.count(),
                'actual_count': type_actual.count(),
                'planned_calories': planned_kcal,
                'actual_calories': actual_kcal,
                'calorie_delta': actual_kcal - planned_kcal,
            }
        )

    entry_count = entries_qs.count()
    insights = _build_insights(
        plan,
        planned_total=planned_totals['calories'],
        actual_total=actual_totals['calories'],
        linked_count=linked_count,
        entry_count=entry_count,
        missing_log_count=missing_log_count,
        extra_count=len(extra_meals),
        daily_rows=daily,
    )

    return {
        'compare_mode': 'db',
        'meal_plan_id': plan.pk,
        'meal_plan_title': plan.title,
        'date_range': {
            'start': str(plan.start_date),
            'end': str(plan.end_date),
        },
        'summary': {
            'planned_entry_count': entry_count,
            'actual_meal_count': actual_qs.count(),
            'linked_entry_count': linked_count,
            'matched_unlinked_count': matched_unlinked_count,
            'missing_log_count': missing_log_count,
            'extra_meal_count': len(extra_meals),
            'adherence_rate': plan.adherence_rate,
            'totals': {
                'planned': planned_totals,
                'actual': actual_totals,
                'calorie_delta': actual_totals['calories'] - planned_totals['calories'],
            },
            'daily_targets': {
                'calories': plan.daily_calorie_target,
                'protein_g': _json_safe(plan.daily_protein_target),
                'carbs_g': _json_safe(plan.daily_carbs_target),
                'fat_g': _json_safe(plan.daily_fat_target),
            },
            'duration_days': duration,
        },
        'daily': daily,
        'by_meal_type': by_type,
        'slots': slots,
        'extra_meals': extra_meals,
        'insights': insights,
    }


def compare_meal_plan_db_response_payload(plan: MealPlan, *, extra: dict | None = None) -> dict[str, Any]:
    """API-ready dict for DB compare endpoints."""
    payload = compare_meal_plan_db(plan)
    if extra:
        payload.update(extra)
    return payload
