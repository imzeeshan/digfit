from auditlog.mixins import AuditlogHistoryAdminMixin
from django.contrib import admin
from django.contrib.admin import AdminSite
from django.utils.translation import gettext_lazy as _

from .models import Intervention, MealEntry, MealPlan, SubscriptionPlan, UserMeal, UserSettings, Weight


class DashboardAdminSite(AdminSite):
    site_header = _('Dashboard Administration')
    site_title = _('Dashboard Admin')
    index_title = _('Welcome to the Dashboard Admin')

dashboard_admin_site = DashboardAdminSite(name='dashboard_admin')


@admin.register(SubscriptionPlan)
class SubscriptionPlanAdmin(AuditlogHistoryAdminMixin, admin.ModelAdmin):
    list_display = ('name', 'slug', 'price', 'interval', 'is_active')
    list_filter = ('interval', 'is_active')
    search_fields = ('name',)
    show_auditlog_history_link = True


@admin.register(UserSettings)
class UserSettingsAdmin(AuditlogHistoryAdminMixin, admin.ModelAdmin):
    list_display = ('user', 'subscription_status', 'subscription_plan', 'created_at')
    list_filter = ('subscription_status',)
    search_fields = ('user__email',)
    raw_id_fields = ('user',)
    show_auditlog_history_link = True


@admin.register(Weight)
class WeightAdmin(AuditlogHistoryAdminMixin, admin.ModelAdmin):
    list_display = ('user', 'value', 'source', 'datetime')
    list_filter = ('source', 'datetime')
    search_fields = ('user__email',)
    raw_id_fields = ('user',)
    ordering = ('-datetime',)
    show_auditlog_history_link = True


class MealEntryInline(admin.TabularInline):
    model = MealEntry
    extra = 1
    fields = ('day_number', 'meal_type', 'title', 'scheduled_time', 'calories', 'protein', 'carbs', 'fat', 'sort_order')


@admin.register(MealPlan)
class MealPlanAdmin(AuditlogHistoryAdminMixin, admin.ModelAdmin):
    list_display = ('user', 'title', 'start_date', 'end_date', 'dietary_preference', 'daily_calorie_target')
    list_filter = ('dietary_preference', 'start_date')
    search_fields = ('user__email', 'title')
    raw_id_fields = ('user',)
    ordering = ('-start_date',)
    show_auditlog_history_link = True
    inlines = [MealEntryInline]


@admin.register(MealEntry)
class MealEntryAdmin(AuditlogHistoryAdminMixin, admin.ModelAdmin):
    list_display = ('meal_plan', 'day_number', 'meal_type', 'title', 'calories')
    list_filter = ('meal_type', 'day_number')
    search_fields = ('title', 'meal_plan__title')
    raw_id_fields = ('meal_plan', 'actual_meal')
    ordering = ('meal_plan', 'day_number', 'sort_order')
    show_auditlog_history_link = True


@admin.register(UserMeal)
class UserMealAdmin(AuditlogHistoryAdminMixin, admin.ModelAdmin):
    list_display = ('user', 'title', 'meal_type', 'calories', 'time_taken')
    list_filter = ('meal_type', 'time_taken')
    search_fields = ('user__email', 'title')
    raw_id_fields = ('user',)
    ordering = ('-time_taken',)
    show_auditlog_history_link = True


@admin.register(Intervention)
class InterventionAdmin(AuditlogHistoryAdminMixin, admin.ModelAdmin):
    list_display = ('user', 'title', 'type', 'status', 'priority', 'scheduled_at')
    list_filter = ('type', 'status', 'priority')
    search_fields = ('user__email', 'title')
    raw_id_fields = ('user',)
    ordering = ('-created_at',)
    show_auditlog_history_link = True
