from django.conf import settings
from django.db import models
from projects.constants import ROLE_CHOICES


class UserProfile(models.Model):
    """Extended profile storing role, department, and contact details for each user."""

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='profile')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='LANDOWNER')
    phone = models.CharField(max_length=20, blank=True)
    address = models.TextField(blank=True)
    employee_id = models.CharField(max_length=50, blank=True)
    designation = models.CharField(max_length=100, blank=True)
    department = models.ForeignKey(
        'projects.Department',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='members',
    )
    is_verified = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.get_full_name() or self.user.username} ({self.get_role_display()})"


class AuditLog(models.Model):
    """Tracks important user actions across the platform for accountability."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='audit_logs',
    )
    action = models.CharField(max_length=100)
    model_name = models.CharField(max_length=100, blank=True)
    object_id = models.CharField(max_length=50, blank=True)
    details = models.TextField(blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        actor = self.user.username if self.user else 'System'
        return f"[{self.created_at:%Y-%m-%d %H:%M}] {actor}: {self.action}"
