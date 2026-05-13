"""LLM-assisted comparison of meal plans vs. logged user meals (Ollama)."""

from __future__ import annotations

import json
from decimal import Decimal
from typing import Any

from django.db.models import Count, Sum
from django.utils import timezone

from core.ollama_client import chat_for_user

from .models import MealPlan, UserMeal


def _json_safe(value: Any) -> Any:
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (list, tuple)):
        return [_json_safe(v) for v in value]
    if isinstance(value, dict):
        return {k: _json_safe(v) for k, v in value.items()}
    return value


def build_meal_comparison_context(plan: MealPlan) -> dict[str, Any]:
    """Structured context for the LLM (planned entries + targets + actual UserMeals in range)."""
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
            'daily_protein_target': _json_safe(plan.daily_protein_target) if plan.daily_protein_target is not None else None,
            'daily_carbs_target': _json_safe(plan.daily_carbs_target) if plan.daily_carbs_target is not None else None,
            'daily_fat_target': _json_safe(plan.daily_fat_target) if plan.daily_fat_target is not None else None,
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


_SYSTEM_PROMPT = """You are a nutrition coach assistant. You compare a structured MEAL PLAN (planned entries and optional daily macro/calorie targets) with ACTUAL MEALS the same user logged in the app during the plan's date window.

Rules:
- Use only the JSON data provided; do not invent foods or weights.
- The object `meal_plan` is the single plan window being analyzed. If `stats.planned_entry_count` is 0, the per-meal row list `planned_entries` is empty in this payload: still use `daily_*_target`, `dietary_preference`, `goal`, and `notes` if present, and compare `actual_meals_in_plan_window` to those targets. Do **not** say there is "no meal plan in the database" or that the plan is "empty" in a global sense—say explicitly that **no per-meal structured entries** were provided in the data for this plan window (or that only targets/notes exist).
- Compare timing/meal types loosely (same calendar day and meal type when relevant).
- Note missing logs, extra meals, calorie drift vs plan/totals, and macro alignment when targets exist.
- Give 3–6 concise, actionable suggestions (bullets OK).
- Keep the answer under ~700 words. Plain text or light markdown headings is fine."""


def resolve_meal_plan_for_user_comparison(user) -> tuple[MealPlan | None, str | None]:
    """Choose one plan for LLM compare.

    Prefer a plan whose dates include **today** and that has **MealEntry** rows; if every
    in-window plan is an empty shell (no entries), fall back to the most recent plan that
    does have entries so the LLM is not fed an empty ``planned_entries`` when another plan
    exists with structured meals.

    Returns ``(plan, selection_reason)`` where ``selection_reason`` is one of:

    - ``active_window`` — dates include today; chosen among overlapping plans by most entries
      then latest ``start_date``.
    - ``fallback_latest_with_entries`` — today fell inside only empty-shell plan(s); using the
      latest plan (by ``start_date``) that has at least one entry instead.
    - ``latest_by_start_date`` — no plan overlaps today; using best plan by entry count then
      ``start_date``.

    ``(None, None)`` if the user has no meal plans at all.
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


def compare_meal_plan_to_logged_meals(plan: MealPlan) -> tuple[str, dict[str, Any]]:
    """Call Ollama (user's host/model from settings) and return (assistant_text, context_dict)."""
    ctx = build_meal_comparison_context(plan)
    payload = json.dumps(ctx, indent=2, default=str)
    messages = [
        {'role': 'system', 'content': _SYSTEM_PROMPT},
        {
            'role': 'user',
            'content': f'Compare this meal plan to the logged meals. Data JSON:\n{payload}',
        },
    ]
    raw = chat_for_user(
        plan.user,
        messages,
        stream=False,
        options={'num_predict': 1200, 'temperature': 0.3},
    )
    if hasattr(raw, 'message') and raw.message:
        text = (raw.message.content or '').strip()
    else:
        text = (raw or {}).get('message', {}).get('content', '').strip()
    if not text:
        text = '(Model returned empty content.)'
    return text, ctx
