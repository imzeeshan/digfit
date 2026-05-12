from django.contrib.auth import get_user_model
from rest_framework import serializers

from apps.dashboard.models import Intervention, MealEntry, MealPlan, SubscriptionPlan, UserMeal, UserSettings, Weight
from apps.subscriptions.models import StripeCustomer

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    profile_pic = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id', 'email', 'name', 'role', 'date_of_birth', 'gender',
            'metadata', 'profile_pic', 'is_active', 'date_joined',
        ]
        read_only_fields = ['id', 'email', 'role', 'is_active', 'date_joined']

    def get_profile_pic(self, obj):
        return obj.metadata.get('profile_pic', '')


class UserProfileUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['name', 'date_of_birth', 'gender', 'metadata']


class SubscriptionPlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = SubscriptionPlan
        fields = [
            'id', 'name', 'slug', 'description', 'price',
            'interval', 'features', 'is_active', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class UserSettingsSerializer(serializers.ModelSerializer):
    subscription_plan_name = serializers.CharField(
        source='subscription_plan.name', read_only=True, default=None,
    )
    is_subscription_active = serializers.BooleanField(read_only=True)
    is_trial_active = serializers.BooleanField(read_only=True)

    class Meta:
        model = UserSettings
        fields = [
            'id', 'notify_comments', 'notify_updates', 'notify_marketing',
            'subscription_plan', 'subscription_plan_name',
            'subscription_status', 'subscription_start_date',
            'subscription_end_date', 'trial_end_date',
            'is_subscription_active', 'is_trial_active',
            'api_key_prefix', 'api_key_created_at',
            'created_at', 'updated_at',
        ]
        read_only_fields = [
            'id', 'subscription_plan', 'subscription_plan_name',
            'subscription_status', 'subscription_start_date',
            'subscription_end_date', 'trial_end_date',
            'is_subscription_active', 'is_trial_active',
            'api_key_prefix', 'api_key_created_at',
            'created_at', 'updated_at',
        ]


class StripeCustomerSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source='user.email', read_only=True)

    class Meta:
        model = StripeCustomer
        fields = [
            'id', 'user_email', 'stripe_customer_id',
            'stripe_subscription_id', 'subscription_status',
            'created_at', 'updated_at',
        ]
        read_only_fields = fields


class WeightSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source='user.email', read_only=True)

    class Meta:
        model = Weight
        fields = [
            'id', 'user', 'user_email', 'datetime', 'value',
            'source', 'metadata',
        ]
        read_only_fields = ['id', 'user']


class MealEntrySerializer(serializers.ModelSerializer):
    meal_type_display = serializers.CharField(source='get_meal_type_display', read_only=True)

    class Meta:
        model = MealEntry
        fields = [
            'id', 'meal_plan',
            'meal_type', 'meal_type_display', 'day_number', 'scheduled_time',
            'title', 'foods_json',
            'calories', 'protein', 'carbs', 'fat',
            'portion_notes', 'substitutions', 'sort_order',
            'actual_meal',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'meal_plan', 'created_at', 'updated_at']


class MealPlanSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source='user.email', read_only=True)
    dietary_preference_display = serializers.CharField(source='get_dietary_preference_display', read_only=True)
    entries = MealEntrySerializer(many=True, read_only=True)
    entry_count = serializers.IntegerField(read_only=True)
    total_calories = serializers.IntegerField(read_only=True)
    adherence_rate = serializers.IntegerField(read_only=True)

    class Meta:
        model = MealPlan
        fields = [
            'id', 'user', 'user_email', 'title',
            'start_date', 'end_date',
            'daily_calorie_target', 'daily_protein_target', 'daily_carbs_target',
            'daily_fat_target', 'daily_water_target_ml',
            'dietary_preference', 'dietary_preference_display',
            'allergies_restrictions', 'supplements',
            'goal', 'notes',
            'entries', 'entry_count', 'total_calories', 'adherence_rate',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'user', 'entries', 'entry_count', 'total_calories', 'adherence_rate', 'created_at', 'updated_at']


class UserMealSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source='user.email', read_only=True)
    meal_type_display = serializers.CharField(source='get_meal_type_display', read_only=True)

    class Meta:
        model = UserMeal
        fields = [
            'id', 'user', 'user_email',
            'meal_type', 'meal_type_display', 'title',
            'time_taken', 'description', 'calories', 'metadata',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'user', 'created_at', 'updated_at']


class InterventionSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source='user.email', read_only=True)
    type_display = serializers.CharField(source='get_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    priority_display = serializers.CharField(source='get_priority_display', read_only=True)

    class Meta:
        model = Intervention
        fields = [
            'id', 'user', 'user_email',
            'type', 'type_display', 'status', 'status_display',
            'priority', 'priority_display',
            'title', 'description',
            'trigger_source', 'target_metric', 'target_value', 'current_value',
            'action_json',
            'scheduled_at', 'completed_at', 'created_by',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'user', 'created_at', 'updated_at']
