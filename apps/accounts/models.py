from datetime import date

from auditlog.registry import auditlog
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models


class CustomUserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('Email is required')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        return self.create_user(email, password, **extra_fields)


class CustomUser(AbstractUser):
    ROLE_CHOICES = [
        ('admin', 'Admin'),
        ('coach', 'Coach'),
        ('user', 'Regular User'),
    ]
    GENDER_CHOICES = [
        ('male', 'Male'),
        ('female', 'Female'),
        ('other', 'Other'),
        ('prefer_not_to_say', 'Prefer not to say'),
    ]

    username = None
    first_name = None
    last_name = None

    email = models.EmailField(unique=True)
    name = models.CharField(max_length=255, blank=True)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='user')
    date_of_birth = models.DateField(null=True, blank=True)
    gender = models.CharField(max_length=20, choices=GENDER_CHOICES, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    objects = CustomUserManager()

    @property
    def is_admin_role(self):
        return self.role == 'admin'

    @property
    def is_coach(self):
        return self.role == 'coach'

    @property
    def is_regular_user(self):
        return self.role == 'user'

    def get_full_name(self):
        return self.name or self.email

    def get_short_name(self):
        return self.name.split()[0] if self.name else self.email

    @property
    def age(self):
        if not self.date_of_birth:
            return None
        today = date.today()
        born = self.date_of_birth
        return today.year - born.year - ((today.month, today.day) < (born.month, born.day))

    @property
    def profile_pic(self):
        return self.metadata.get('profile_pic', '')

    def __str__(self):
        return self.email


auditlog.register(
    CustomUser,
    exclude_fields=['password', 'last_login'],
)
