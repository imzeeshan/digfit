from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.authtoken.models import Token

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
