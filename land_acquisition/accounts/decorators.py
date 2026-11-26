from functools import wraps
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect
from .models import AuditLog, UserProfile


def get_user_role(user):
    """Return the role code for an authenticated user, creating a default profile if missing."""
    if not user.is_authenticated:
        return None
    if user.is_superuser:
        profile, _ = UserProfile.objects.get_or_create(user=user, defaults={'role': 'ADMIN'})
        return profile.role
    profile, _ = UserProfile.objects.get_or_create(user=user, defaults={'role': 'LANDOWNER'})
    return profile.role


def role_required(*allowed_roles):
    """Restrict view access to users with one of the specified roles."""

    def decorator(view_func):
        @login_required
        @wraps(view_func)
        def _wrapped(request, *args, **kwargs):
            role = get_user_role(request.user)
            if role in allowed_roles or request.user.is_superuser:
                return view_func(request, *args, **kwargs)
            messages.error(request, 'Access denied: you do not have permission to view this page.')
            return redirect('accounts:dashboard_redirect')

        return _wrapped

    return decorator


def get_client_ip(request):
    """Extract client IP address from request headers."""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')


def log_audit(request, action, model_name='', object_id='', details=''):
    """Create an AuditLog entry for important user actions."""
    user = request.user if request and request.user.is_authenticated else None
    ip = get_client_ip(request) if request else None
    AuditLog.objects.create(
        user=user,
        action=action,
        model_name=model_name,
        object_id=str(object_id) if object_id else '',
        details=details,
        ip_address=ip,
    )
