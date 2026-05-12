from auditlog.mixins import AuditlogHistoryAdminMixin
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import CustomUser


@admin.register(CustomUser)
class CustomUserAdmin(AuditlogHistoryAdminMixin, UserAdmin):
    list_display = ('email', 'name', 'role', 'gender', 'is_staff', 'is_active', 'date_joined')
    list_filter = ('role', 'is_staff', 'is_active', 'gender', 'date_joined')
    search_fields = ('email', 'name')
    ordering = ('-date_joined',)
    show_auditlog_history_link = True

    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Personal Info', {'fields': ('name', 'role', 'date_of_birth', 'gender', 'metadata')}),
        ('Permissions', {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
        }),
        ('Important Dates', {'fields': ('last_login', 'date_joined')}),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'role', 'password1', 'password2'),
        }),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('stripecustomer')
