from django.contrib import admin
from .models import AuditLog, UserProfile


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'role', 'department', 'employee_id', 'phone', 'is_verified')
    list_filter = ('role', 'is_verified', 'department')
    search_fields = ('user__username', 'user__first_name', 'user__last_name', 'employee_id')


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ('created_at', 'user', 'action', 'model_name', 'object_id', 'ip_address')
    list_filter = ('action', 'model_name')
    search_fields = ('user__username', 'details', 'action')
