from django.conf import settings
from django.db import models
from projects.validators import validate_document_file, validate_image_file


class SurveyAssignment(models.Model):
    """Links a land parcel to an assigned field surveyor."""

    SURVEY_STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('ASSIGNED', 'Assigned'),
        ('IN_PROGRESS', 'In Progress'),
        ('SUBMITTED', 'Submitted'),
        ('VERIFIED', 'Verified'),
        ('REJECTED', 'Rejected'),
    ]

    land_record = models.ForeignKey(
        'land_records.LandRecord',
        on_delete=models.CASCADE,
        related_name='survey_assignments',
    )
    project = models.ForeignKey(
        'projects.AcquisitionProject',
        on_delete=models.CASCADE,
        related_name='survey_assignments',
    )
    surveyor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='assigned_surveys',
    )
    assigned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_survey_assignments',
    )
    assigned_date = models.DateField(auto_now_add=True)
    due_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=SURVEY_STATUS_CHOICES, default='ASSIGNED')
    instructions = models.TextField(blank=True)
    officer_remarks = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Survey #{self.id} - {self.land_record} ({self.get_status_display()})"

    @property
    def status_badge(self):
        return {
            'PENDING': 'secondary',
            'ASSIGNED': 'primary',
            'IN_PROGRESS': 'warning',
            'SUBMITTED': 'info',
            'VERIFIED': 'success',
            'REJECTED': 'danger',
        }.get(self.status, 'secondary')


class SurveyReport(models.Model):
    """Field inspection report submitted by a surveyor and verified by an officer."""

    assignment = models.OneToOneField(SurveyAssignment, on_delete=models.CASCADE, related_name='report')
    actual_area_acres = models.DecimalField(max_digits=10, decimal_places=2)
    verified_land_type = models.CharField(max_length=50)
    current_land_usage = models.CharField(max_length=200)
    boundary_verified = models.BooleanField(default=True)
    encroachment_found = models.BooleanField(default=False)
    structures_present = models.CharField(max_length=255, blank=True)
    trees_crops_details = models.CharField(max_length=255, blank=True)
    inspection_date = models.DateField()
    inspection_remarks = models.TextField()
    photo_1 = models.ImageField(
        upload_to='surveys/photos/%Y/%m/',
        null=True,
        blank=True,
        validators=[validate_image_file],
    )
    photo_2 = models.ImageField(
        upload_to='surveys/photos/%Y/%m/',
        null=True,
        blank=True,
        validators=[validate_image_file],
    )
    report_document = models.FileField(
        upload_to='surveys/docs/%Y/%m/',
        null=True,
        blank=True,
        validators=[validate_document_file],
    )
    submitted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='submitted_reports',
    )
    verified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='verified_reports',
    )
    verified_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Report for {self.assignment.land_record}"
