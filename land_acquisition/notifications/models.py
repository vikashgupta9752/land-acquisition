from django.conf import settings
from django.db import models
from projects.validators import validate_document_file


class Notification(models.Model):
    """Internal alerts and official acquisition notifications."""

    NOTIFICATION_TYPES = [
        ('OFFICIAL_NOTICE', 'Official Acquisition Notification'),
        ('SURVEY_UPDATE', 'Survey Update'),
        ('OBJECTION_UPDATE', 'Objection Update'),
        ('COMPENSATION_UPDATE', 'Compensation Update'),
        ('PAYMENT_UPDATE', 'Payment Update'),
        ('POSSESSION_UPDATE', 'Possession Update'),
        ('PROJECT_UPDATE', 'Project Update'),
    ]

    project = models.ForeignKey(
        'projects.AcquisitionProject',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='notifications',
    )
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='notifications',
    )
    is_official_notice = models.BooleanField(default=False)
    notice_number = models.CharField(max_length=60, blank=True)
    title = models.CharField(max_length=200)
    message = models.TextField()
    notification_type = models.CharField(max_length=25, choices=NOTIFICATION_TYPES, default='PROJECT_UPDATE')
    is_read = models.BooleanField(default=False)
    attachment = models.FileField(
        upload_to='notifications/%Y/%m/',
        null=True,
        blank=True,
        validators=[validate_document_file],
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='sent_notifications',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.title} ({self.get_notification_type_display()})"
