"""LLM-assisted comparison of meal plans vs. logged user meals (Ollama)."""

from __future__ import annotations

import json
from typing import Any

from core.ollama_client import chat_for_user

from .meal_plan_compare import (  # noqa: F401
    build_meal_comparison_context,
    resolve_meal_plan_for_user_comparison,
)
from .models import MealPlan

_SYSTEM_PROMPT = """You are a nutrition coach assistant. You compare a structured MEAL PLAN (planned entries and optional daily macro/calorie targets) with ACTUAL MEALS the same user logged in the app during the plan's date window.

Rules:
- Use only the JSON data provided; do not invent foods or weights.
- The object `meal_plan` is the single plan window being analyzed. If `stats.planned_entry_count` is 0, the per-meal row list `planned_entries` is empty in this payload: still use `daily_*_target`, `dietary_preference`, `goal`, and `notes` if present, and compare `actual_meals_in_plan_window` to those targets. Do **not** say there is "no meal plan in the database" or that the plan is "empty" in a global sense—say explicitly that **no per-meal structured entries** were provided in the data for this plan window (or that only targets/notes exist).
- Compare timing/meal types loosely (same calendar day and meal type when relevant).
- Note missing logs, extra meals, calorie drift vs plan/totals, and macro alignment when targets exist.
- Give 3–6 concise, actionable suggestions (bullets OK).
- Keep the answer under ~700 words. Plain text or light markdown headings is fine."""


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
