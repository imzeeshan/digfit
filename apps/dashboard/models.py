from auditlog.registry import auditlog
from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils import timezone


class SubscriptionPlan(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    interval = models.CharField(
        max_length=20,
        choices=[
            ('monthly', 'Monthly'),
            ('yearly', 'Yearly'),
        ],
        default='monthly'
    )
    features = models.JSONField(default=list)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Subscription Plan'
        verbose_name_plural = 'Subscription Plans'

    def __str__(self):
        return f"{self.name} ({self.get_interval_display()})"

class UserSettings(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='settings'
    )
    # Notification preferences
    notify_comments = models.BooleanField(default=False)
    notify_updates = models.BooleanField(default=False)
    notify_marketing = models.BooleanField(default=False)

    # Ollama (local LLM); empty strings fall back to Django settings OLLAMA_HOST / OLLAMA_MODEL
    ollama_host = models.CharField(max_length=500, blank=True, default='')
    ollama_model = models.CharField(max_length=200, blank=True, default='')

    # API settings
    api_key_hash = models.CharField(max_length=64, blank=True, default='')
    api_key_prefix = models.CharField(max_length=12, blank=True, default='')
    api_key_created_at = models.DateTimeField(null=True, blank=True)

    # Subscription settings
    subscription_plan = models.ForeignKey(
        SubscriptionPlan,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='subscribers'
    )
    subscription_status = models.CharField(
        max_length=20,
        choices=[
            ('active', 'Active'),
            ('inactive', 'Inactive'),
            ('cancelled', 'Cancelled'),
            ('trial', 'Trial'),
        ],
        default='inactive'
    )
    subscription_start_date = models.DateTimeField(null=True, blank=True)
    subscription_end_date = models.DateTimeField(null=True, blank=True)
    trial_end_date = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'User Settings'
        verbose_name_plural = 'User Settings'

    def __str__(self):
        return f"Settings for {self.user.email}"

    def get_effective_ollama_host(self) -> str:
        from django.conf import settings as django_settings

        v = (self.ollama_host or '').strip()
        return v or django_settings.OLLAMA_HOST

    def get_effective_ollama_model(self) -> str:
        from django.conf import settings as django_settings

        v = (self.ollama_model or '').strip()
        return v or django_settings.OLLAMA_MODEL

    @property
    def is_subscription_active(self):
        if self.subscription_status != 'active':
            return False
        if self.subscription_end_date and self.subscription_end_date < timezone.now():
            return False
        return True

    @property
    def is_trial_active(self):
        if self.subscription_status != 'trial':
            return False
        if self.trial_end_date and self.trial_end_date < timezone.now():
            return False
        return True


class Weight(models.Model):
    SOURCE_CHOICES = [
        ('manual', 'Manual'),
        ('api', 'API'),
        ('import', 'Import'),
        ('device', 'Device'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='weights',
    )
    datetime = models.DateTimeField()
    value = models.DecimalField(max_digits=6, decimal_places=2, help_text='Weight in lbs')
    source = models.CharField(max_length=20, choices=SOURCE_CHOICES, default='manual')
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        verbose_name = 'Weight Entry'
        verbose_name_plural = 'Weight Entries'
        ordering = ['-datetime']
        indexes = [
            models.Index(fields=['user', '-datetime']),
        ]

    def __str__(self):
        return f"{self.user.email} — {self.value} lbs @ {self.datetime:%Y-%m-%d %H:%M}"

    def get_absolute_url(self):
        return reverse('dashboard:weight_detail', kwargs={'pk': self.pk})


class MealPlan(models.Model):
    DIETARY_CHOICES = [
        ('none', 'No Preference'),
        ('vegetarian', 'Vegetarian'),
        ('vegan', 'Vegan'),
        ('keto', 'Keto'),
        ('high_protein', 'High Protein'),
        ('paleo', 'Paleo'),
        ('mediterranean', 'Mediterranean'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='meal_plans',
    )
    title = models.CharField(max_length=255)
    start_date = models.DateField()
    end_date = models.DateField()

    daily_calorie_target = models.IntegerField(null=True, blank=True)
    daily_protein_target = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    daily_carbs_target = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    daily_fat_target = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    daily_water_target_ml = models.IntegerField(null=True, blank=True)

    dietary_preference = models.CharField(max_length=30, choices=DIETARY_CHOICES, default='none')
    allergies_restrictions = models.JSONField(default=list, blank=True)
    supplements = models.JSONField(default=list, blank=True)

    goal = models.CharField(max_length=100, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Meal Plan'
        verbose_name_plural = 'Meal Plans'
        ordering = ['-start_date']
        indexes = [
            models.Index(fields=['user', '-start_date']),
        ]

    def __str__(self):
        return f"{self.user.email} — {self.title} ({self.start_date} to {self.end_date})"

    def get_absolute_url(self):
        return reverse('dashboard:meal_detail', kwargs={'pk': self.pk})

    @property
    def total_calories(self):
        return self.entries.aggregate(total=models.Sum('calories'))['total'] or 0

    @property
    def total_protein(self):
        return self.entries.aggregate(total=models.Sum('protein'))['total'] or 0

    @property
    def total_carbs(self):
        return self.entries.aggregate(total=models.Sum('carbs'))['total'] or 0

    @property
    def total_fat(self):
        return self.entries.aggregate(total=models.Sum('fat'))['total'] or 0

    @property
    def entry_count(self):
        return self.entries.count()

    @property
    def adherence_rate(self):
        total = self.entries.count()
        if not total:
            return 0
        linked = self.entries.filter(actual_meal__isnull=False).count()
        return round(linked / total * 100)

    @property
    def duration_days(self):
        if self.start_date and self.end_date:
            return (self.end_date - self.start_date).days + 1
        return 0


class MealEntry(models.Model):
    MEAL_TYPE_CHOICES = [
        ('breakfast', 'Breakfast'),
        ('mid_morning_snack', 'Mid-morning Snack'),
        ('lunch', 'Lunch'),
        ('evening_snack', 'Evening Snack'),
        ('dinner', 'Dinner'),
        ('post_workout', 'Post-workout'),
        ('bedtime_snack', 'Bedtime Snack'),
    ]

    meal_plan = models.ForeignKey(
        MealPlan,
        on_delete=models.CASCADE,
        related_name='entries',
    )
    meal_type = models.CharField(max_length=30, choices=MEAL_TYPE_CHOICES)
    day_number = models.PositiveIntegerField(help_text='Day of the plan (1, 2, 3...)')
    scheduled_time = models.TimeField(null=True, blank=True)
    title = models.CharField(max_length=255)
    foods_json = models.JSONField(default=list, blank=True)
    calories = models.IntegerField(default=0)
    protein = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    carbs = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    fat = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    portion_notes = models.CharField(max_length=255, blank=True)
    substitutions = models.JSONField(default=list, blank=True)
    sort_order = models.IntegerField(default=0)
    actual_meal = models.ForeignKey(
        'UserMeal',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='planned_entries',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Meal Entry'
        verbose_name_plural = 'Meal Entries'
        ordering = ['day_number', 'sort_order']
        indexes = [
            models.Index(fields=['meal_plan', 'day_number']),
        ]

    def __str__(self):
        return f"Day {self.day_number} — {self.get_meal_type_display()}: {self.title}"

    def get_absolute_url(self):
        return reverse('dashboard:meal_detail', kwargs={'pk': self.meal_plan_id})


class UserMeal(models.Model):
    MEAL_TYPE_CHOICES = [
        ('breakfast', 'Breakfast'),
        ('mid_morning_snack', 'Mid-morning Snack'),
        ('lunch', 'Lunch'),
        ('evening_snack', 'Evening Snack'),
        ('dinner', 'Dinner'),
        ('post_workout', 'Post-workout'),
        ('bedtime_snack', 'Bedtime Snack'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='user_meals',
    )
    meal_type = models.CharField(max_length=20, choices=MEAL_TYPE_CHOICES)
    title = models.CharField(max_length=255)
    time_taken = models.DateTimeField()
    description = models.TextField(blank=True)
    calories = models.IntegerField(default=0)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'User Meal'
        verbose_name_plural = 'User Meals'
        ordering = ['-time_taken']
        indexes = [
            models.Index(fields=['user', '-time_taken']),
        ]

    def __str__(self):
        return f"{self.user.email} — {self.title} @ {self.time_taken:%Y-%m-%d %H:%M}"

    def get_absolute_url(self):
        return reverse('dashboard:usermeal_detail', kwargs={'pk': self.pk})


class Intervention(models.Model):
    TYPE_CHOICES = [
        ('dietary', 'Dietary'),
        ('exercise', 'Exercise'),
        ('behavioral', 'Behavioral'),
        ('medical', 'Medical'),
        ('supplement', 'Supplement'),
        ('other', 'Other'),
    ]
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('active', 'Active'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
        ('skipped', 'Skipped'),
    ]
    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('normal', 'Normal'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='interventions',
    )
    type = models.CharField(max_length=50, choices=TYPE_CHOICES)
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='pending')
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default='normal')
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    trigger_source = models.CharField(max_length=100, blank=True)
    target_metric = models.CharField(max_length=100, blank=True)
    target_value = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    current_value = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    action_json = models.JSONField(default=dict, blank=True)
    scheduled_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_by = models.CharField(max_length=50, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Intervention'
        verbose_name_plural = 'Interventions'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['status']),
        ]

    def __str__(self):
        return f"{self.user.email} — {self.title} ({self.get_status_display()})"

    def get_absolute_url(self):
        return reverse('dashboard:intervention_detail', kwargs={'pk': self.pk})


auditlog.register(SubscriptionPlan)
auditlog.register(
    UserSettings,
    exclude_fields=['api_key_hash'],
)
auditlog.register(Weight)
auditlog.register(MealPlan)
auditlog.register(MealEntry)
auditlog.register(UserMeal)
auditlog.register(Intervention)
