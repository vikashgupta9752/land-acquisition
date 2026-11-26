from notifications.models import Notification


def unread_notifications(request):
    """Provide unread notification count and recent notifications to all templates."""
    if request.user.is_authenticated:
        qs = Notification.objects.filter(recipient=request.user)
        return {
            'unread_notification_count': qs.filter(is_read=False).count(),
            'recent_notifications': qs[:5],
        }
    return {
        'unread_notification_count': 0,
        'recent_notifications': [],
    }
