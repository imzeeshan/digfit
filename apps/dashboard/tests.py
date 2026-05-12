import hashlib

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .models import SubscriptionPlan, UserSettings

User = get_user_model()


class DashboardAccessTests(TestCase):
    def test_dashboard_redirects_anonymous(self):
        response = self.client.get('/dashboard/')
        self.assertEqual(response.status_code, 302)

    def test_profile_redirects_anonymous(self):
        response = self.client.get('/dashboard/profile/')
        self.assertEqual(response.status_code, 302)

    def test_settings_redirects_anonymous(self):
        response = self.client.get('/dashboard/settings/')
        self.assertEqual(response.status_code, 302)

    def test_dashboard_accessible_when_logged_in(self):
        user = User.objects.create_user(email='test@example.com', password='testpass123')
        self.client.force_login(user)
        response = self.client.get('/dashboard/')
        self.assertEqual(response.status_code, 200)


class SubscriptionPlanModelTests(TestCase):
    def test_create_plan(self):
        plan = SubscriptionPlan.objects.create(
            name='Pro', slug='pro', description='Pro plan', price=9.99, interval='monthly', features=['API access'],
        )
        self.assertEqual(str(plan), 'Pro (Monthly)')
        self.assertTrue(plan.is_active)

    def test_user_settings_created_on_access(self):
        user = User.objects.create_user(email='test@example.com', password='testpass123')
        settings, created = UserSettings.objects.get_or_create(user=user)
        self.assertTrue(created)
        self.assertEqual(settings.subscription_status, 'inactive')


class ApiKeyHashingTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email='test@example.com', password='testpass123')
        self.client.force_login(self.user)

    def test_generate_api_key_stores_only_hash(self):
        self.client.post(reverse('dashboard:generate_api_key'))
        settings = UserSettings.objects.get(user=self.user)
        plaintext = self.client.session['new_api_key']

        self.assertEqual(len(settings.api_key_hash), 64)
        self.assertNotEqual(settings.api_key_hash, plaintext)
        self.assertEqual(settings.api_key_hash, hashlib.sha256(plaintext.encode()).hexdigest())

    def test_api_key_prefix_stored_for_display(self):
        self.client.post(reverse('dashboard:generate_api_key'))
        settings = UserSettings.objects.get(user=self.user)
        plaintext = self.client.session['new_api_key']

        self.assertEqual(settings.api_key_prefix, plaintext[:8])

    def test_regenerating_key_replaces_hash(self):
        self.client.post(reverse('dashboard:generate_api_key'))
        first_hash = UserSettings.objects.get(user=self.user).api_key_hash

        self.client.post(reverse('dashboard:generate_api_key'))
        second_hash = UserSettings.objects.get(user=self.user).api_key_hash

        self.assertNotEqual(first_hash, second_hash)


class SettingsOllamaTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email='ollama@example.com', password='testpass123')
        self.client.force_login(self.user)

    def test_settings_saves_ollama_fields(self):
        self.client.post(
            reverse('dashboard:settings'),
            {
                'comments': 'on',
                'ollama_host': 'http://127.0.0.1:11434',
                'ollama_model': 'medgemma:4b',
            },
        )
        us = UserSettings.objects.get(user=self.user)
        self.assertTrue(us.notify_comments)
        self.assertEqual(us.ollama_host, 'http://127.0.0.1:11434')
        self.assertEqual(us.ollama_model, 'medgemma:4b')

    def test_effective_ollama_falls_back_when_blank(self):
        us = UserSettings.objects.create(user=self.user)
        self.assertEqual(us.ollama_host, '')
        self.assertIn('127.0.0.1', us.get_effective_ollama_host())
        self.assertTrue(us.get_effective_ollama_model())
