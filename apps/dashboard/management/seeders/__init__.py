"""Demo data seeders for `manage.py seed_data`."""

from .interventions import seed_interventions
from .meals import seed_meal_plans, seed_user_meals
from .plans import seed_plans
from .user_settings import seed_user_settings
from .users import DEMO_EMAILS, seed_users
from .weights import seed_weights

__all__ = [
    'DEMO_EMAILS',
    'seed_users',
    'seed_plans',
    'seed_user_settings',
    'seed_weights',
    'seed_user_meals',
    'seed_meal_plans',
    'seed_interventions',
]
