from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework.authtoken.models import Token

from apps.dashboard.meal_plan_compare import (
    compare_meal_plan_db,
    resolve_meal_plan_for_user_comparison,
)
from apps.dashboard.models import MealEntry, MealPlan, UserMeal

User = get_user_model()


class AuthTokenApiTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email='apitoken@test.com', password='good-password-1')

    def test_login_returns_token(self):
        response = self.client.post(
            '/api/auth/login/',
            {'email': 'apitoken@test.com', 'password': 'good-password-1'},
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('token', data)
        self.assertTrue(Token.objects.filter(user=self.user, key=data['token']).exists())

    def test_login_invalid_password(self):
        response = self.client.post(
            '/api/auth/login/',
            {'email': 'apitoken@test.com', 'password': 'wrong'},
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 400)

    def test_logout_deletes_token(self):
        token = Token.objects.create(user=self.user)
        response = self.client.post(
            '/api/auth/logout/',
            HTTP_AUTHORIZATION=f'Token {token.key}',
        )
        self.assertEqual(response.status_code, 204)
        self.assertFalse(Token.objects.filter(user=self.user).exists())

    def test_api_root_lists_collections_and_auth(self):
        self.client.force_login(self.user)
        response = self.client.get('/api/')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('users', data)
        self.assertIn('meal-plans', data)
        self.assertIn('auth-login', data)
        self.assertIn('auth-logout', data)
        self.assertTrue(str(data['auth-login']).rstrip('/').endswith('/api/auth/login'))
        self.assertTrue(str(data['auth-logout']).rstrip('/').endswith('/api/auth/logout'))


class ResolveMealPlanForComparisonTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email='resolvemp@test.com', password='pw')

    def test_fallback_when_active_window_plan_has_no_entries(self):
        today = timezone.now().date()
        past_start = today - timedelta(days=30)
        past_end = today - timedelta(days=1)
        past = MealPlan.objects.create(
            user=self.user,
            title='Filled past',
            start_date=past_start,
            end_date=past_end,
        )
        MealEntry.objects.create(
            meal_plan=past,
            meal_type='breakfast',
            day_number=1,
            title='Oats',
            calories=300,
        )
        MealPlan.objects.create(
            user=self.user,
            title='Empty current',
            start_date=today,
            end_date=today + timedelta(days=7),
        )
        plan, reason = resolve_meal_plan_for_user_comparison(self.user)
        self.assertEqual(reason, 'fallback_latest_with_entries')
        self.assertEqual(plan.pk, past.pk)

    def test_active_window_prefers_plan_with_more_entries(self):
        today = timezone.now().date()
        sparse = MealPlan.objects.create(
            user=self.user,
            title='Sparse',
            start_date=today,
            end_date=today,
        )
        MealEntry.objects.create(
            meal_plan=sparse,
            meal_type='breakfast',
            day_number=1,
            title='A',
            calories=100,
        )
        dense = MealPlan.objects.create(
            user=self.user,
            title='Dense',
            start_date=today,
            end_date=today,
        )
        for i in range(3):
            MealEntry.objects.create(
                meal_plan=dense,
                meal_type='lunch',
                day_number=1,
                title=f'M{i}',
                calories=200,
                sort_order=i,
            )
        plan, reason = resolve_meal_plan_for_user_comparison(self.user)
        self.assertEqual(reason, 'active_window')
        self.assertEqual(plan.pk, dense.pk)


class CompareMealPlanDbTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email='dbcmp@test.com', password='pw')
        self.token = Token.objects.create(user=self.user)
        today = timezone.now().date()
        self.plan = MealPlan.objects.create(
            user=self.user,
            title='Test plan',
            start_date=today,
            end_date=today + timedelta(days=1),
            daily_calorie_target=2000,
        )
        self.entry_breakfast = MealEntry.objects.create(
            meal_plan=self.plan,
            meal_type='breakfast',
            day_number=1,
            title='Planned oats',
            calories=400,
        )
        self.entry_lunch = MealEntry.objects.create(
            meal_plan=self.plan,
            meal_type='lunch',
            day_number=1,
            title='Planned salad',
            calories=500,
        )
        self.logged_lunch = UserMeal.objects.create(
            user=self.user,
            meal_type='lunch',
            title='Actual salad',
            time_taken=timezone.now().replace(hour=12, minute=30),
            calories=550,
        )
        self.entry_lunch.actual_meal = self.logged_lunch
        self.entry_lunch.save(update_fields=['actual_meal'])
        self.extra_snack = UserMeal.objects.create(
            user=self.user,
            meal_type='evening_snack',
            title='Unplanned snack',
            time_taken=timezone.now().replace(hour=16, minute=0),
            calories=200,
        )

    def test_compare_meal_plan_db_structure(self):
        result = compare_meal_plan_db(self.plan)
        self.assertEqual(result['compare_mode'], 'db')
        self.assertEqual(result['summary']['linked_entry_count'], 1)
        self.assertEqual(result['summary']['missing_log_count'], 1)
        self.assertEqual(result['summary']['extra_meal_count'], 1)
        self.assertEqual(len(result['slots']), 2)
        statuses = {s['planned_title']: s['status'] for s in result['slots']}
        self.assertEqual(statuses['Planned oats'], 'missing_log')
        self.assertEqual(statuses['Planned salad'], 'linked')
        self.assertTrue(any('extra' in i.lower() or '1 meal' in i for i in result['insights']))

    def test_compare_meals_db_api_by_plan_id(self):
        response = self.client.post(
            f'/api/meal-plans/{self.plan.pk}/compare-meals-db/',
            HTTP_AUTHORIZATION=f'Token {self.token.key}',
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['compare_mode'], 'db')
        self.assertEqual(data['meal_plan_id'], self.plan.pk)
        self.assertIn('slots', data)
        self.assertIn('insights', data)

    def test_compare_meals_db_api_by_user_id(self):
        response = self.client.post(
            f'/api/meal-plans/by-user/{self.user.pk}/compare-meals-db/',
            HTTP_AUTHORIZATION=f'Token {self.token.key}',
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['compare_mode'], 'db')
