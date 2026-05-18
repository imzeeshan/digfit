import hashlib

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from django.utils import timezone

from .models import Notification, SubscriptionPlan, UserSettings, Weight
from .notifications import dismiss_notification, sync_user_notifications

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


class WeightReminderNotificationTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email='weight@example.com', password='testpass123')
        self.settings = UserSettings.objects.create(user=self.user, weight_reminder_days=5)

    def test_no_notification_when_recent_weight_logged(self):
        Weight.objects.create(
            user=self.user,
            datetime=timezone.now(),
            value=180,
        )
        active = sync_user_notifications(self.user)
        self.assertEqual(active, [])
        self.assertFalse(
            Notification.objects.filter(
                user=self.user,
                notification_type=Notification.TYPE_WEIGHT_LOG_OVERDUE,
            ).exists(),
        )

    def test_creates_overdue_notification(self):
        Weight.objects.create(
            user=self.user,
            datetime=timezone.now() - timezone.timedelta(days=10),
            value=180,
        )
        active = sync_user_notifications(self.user)
        self.assertEqual(len(active), 1)
        notif = active[0]
        self.assertEqual(notif.title, 'Weight log overdue')
        self.assertIn('5 days', notif.message)
        self.assertEqual(notif.action_label, 'Log weight')

    def test_dismiss_hides_from_active_list(self):
        Weight.objects.create(
            user=self.user,
            datetime=timezone.now() - timezone.timedelta(days=10),
            value=180,
        )
        active = sync_user_notifications(self.user)
        dismiss_notification(active[0])
        active = sync_user_notifications(self.user)
        self.assertEqual(active, [])

    def test_logging_weight_clears_notification(self):
        Weight.objects.create(
            user=self.user,
            datetime=timezone.now() - timezone.timedelta(days=10),
            value=180,
        )
        sync_user_notifications(self.user)
        Weight.objects.create(
            user=self.user,
            datetime=timezone.now(),
            value=179,
        )
        active = sync_user_notifications(self.user)
        self.assertEqual(active, [])

    def test_dashboard_shows_notification_bell(self):
        Weight.objects.create(
            user=self.user,
            datetime=timezone.now() - timezone.timedelta(days=10),
            value=180,
        )
        self.client.force_login(self.user)
        response = self.client.get(reverse('dashboard:home'))
        self.assertContains(response, 'Weight log overdue')
        self.assertContains(response, 'Log weight')
        self.assertContains(response, 'fa-bell')
        self.assertContains(response, 'Notifications')

    def test_landing_home_shows_notification_bell_and_alert(self):
        Weight.objects.create(
            user=self.user,
            datetime=timezone.now() - timezone.timedelta(days=10),
            value=180,
        )
        self.client.force_login(self.user)
        response = self.client.get(reverse('landing:home'))
        self.assertContains(response, 'Weight log overdue')
        self.assertContains(response, 'Log weight')
        self.assertContains(response, 'fa-bell')

    def test_dismiss_notification_view(self):
        Weight.objects.create(
            user=self.user,
            datetime=timezone.now() - timezone.timedelta(days=10),
            value=180,
        )
        sync_user_notifications(self.user)
        notif = Notification.objects.get(user=self.user)
        self.client.force_login(self.user)
        response = self.client.post(reverse('dashboard:notification_dismiss', args=[notif.pk]))
        self.assertEqual(response.status_code, 302)
        notif.refresh_from_db()
        self.assertTrue(notif.is_dismissed)
