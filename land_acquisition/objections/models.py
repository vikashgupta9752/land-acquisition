from django.conf import settings
from django.db import models
from projects.validators import validate_document_file


class Objection(models.Model):
    """Formal objection or grievance filed by a landowner."""

    OBJECTION_CATEGORIES = [
        ('VALUATION', 'Compensation Valuation Dispute'),
        ('AREA_DISPUTE', 'Land Area Measurement Dispute'),
        ('OWNERSHIP', 'Ownership / Title Correction'),
        ('BOUNDARY', 'Boundary / Survey Number Issue'),
        ('RELOCATION', 'Rehabilitation & Relocation Request'),
        ('OTHER', 'Other Grievance'),
    ]

    OBJECTION_STATUSES = [
        ('SUBMITTED', 'Submitted'),
        ('UNDER_REVIEW', 'Under Review'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected'),
    ]

    land_record = models.ForeignKey(
        'land_records.LandRecord',
        on_delete=models.CASCADE,
        related_name='objections',
    )
    project = models.ForeignKey(
        'projects.AcquisitionProject',
        on_delete=models.CASCADE,
        related_name='objections',
    )
    landowner = models.ForeignKey(
        'land_records.Landowner',
        on_delete=models.CASCADE,
        related_name='objections',
    )
    subject = models.CharField(max_length=200)
    category = models.CharField(max_length=25, choices=OBJECTION_CATEGORIES, default='VALUATION')
    description = models.TextField()
    supporting_document = models.FileField(
        upload_to='objections/%Y/%m/',
        null=True,
        blank=True,
        validators=[validate_document_file],
    )
    status = models.CharField(max_length=20, choices=OBJECTION_STATUSES, default='SUBMITTED')
    officer_remarks = models.TextField(blank=True)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reviewed_objections',
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Objection #{self.id}: {self.subject} ({self.get_status_display()})"

    @property
    def status_badge(self):
        return {
            'SUBMITTED': 'danger',
            'UNDER_REVIEW': 'warning',
            'APPROVED': 'success',
            'REJECTED': 'secondary',
        }.get(self.status, 'secondary')
