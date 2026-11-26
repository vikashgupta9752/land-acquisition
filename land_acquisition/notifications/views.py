from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from .models import Notification


@login_required
def notification_list(request):
    """Display personal notifications and official notices for the logged-in user."""
    personal_notifications = Notification.objects.filter(recipient=request.user).select_related('project')
    return render(request, 'notifications/notification_list.html', {
        'notifications': personal_notifications,
    })


@login_required
def mark_read(request, pk):
    """Mark a single notification as read."""
    notif = get_object_or_404(Notification, pk=pk, recipient=request.user)
    notif.is_read = True
    notif.save(update_fields=['is_read', 'updated_at'])
    return redirect('notifications:list')


@login_required
def mark_all_read(request):
    """Mark all notifications for the current user as read."""
    Notification.objects.filter(recipient=request.user, is_read=False).update(is_read=True)
    return redirect('notifications:list')
