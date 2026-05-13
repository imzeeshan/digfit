from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework.authtoken.models import Token

from apps.dashboard.meal_plan_llm import resolve_meal_plan_for_user_comparison
from apps.dashboard.models import MealEntry, MealPlan

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
