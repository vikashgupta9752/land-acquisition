from datetime import date
from django.conf import settings
from django.db import models
from django.utils import timezone
from .constants import ACQUISITION_STATUS_CHOICES, STATUS_BADGE_MAP, STATUS_ORDER
from .validators import validate_document_file


class Department(models.Model):
    """Government department sponsoring or executing land acquisition projects."""

    name = models.CharField(max_length=150, unique=True)
    code = models.CharField(max_length=30, unique=True)
    description = models.TextField(blank=True)
    head_name = models.CharField(max_length=120, blank=True)
    contact_email = models.EmailField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.code})"


class AcquisitionProject(models.Model):
    """Central land acquisition project entity."""

    project_code = models.CharField(max_length=40, unique=True)
    name = models.CharField(max_length=200)
    purpose = models.CharField(max_length=255)
    department = models.ForeignKey(Department, on_delete=models.PROTECT, related_name='projects')
    assigned_officer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_projects',
    )
    state = models.CharField(max_length=100, default='Maharashtra')
    district = models.CharField(max_length=100)
    taluka = models.CharField(max_length=100, blank=True)
    village = models.CharField(max_length=120)
    required_area_acres = models.DecimalField(max_digits=12, decimal_places=2)
    acquired_area_acres = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    boundary_geojson = models.TextField(blank=True)
    status = models.CharField(
        max_length=35,
        choices=ACQUISITION_STATUS_CHOICES,
        default='PROJECT_CREATED',
    )
    start_date = models.DateField(default=date.today)
    target_completion_date = models.DateField(null=True, blank=True)
    description = models.TextField(blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_projects',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.project_code} - {self.name}"

    @property
    def status_badge(self):
        return STATUS_BADGE_MAP.get(self.status, 'secondary')

    @property
    def progress_percent(self):
        step = STATUS_ORDER.get(self.status, 1)
        return round((step / len(ACQUISITION_STATUS_CHOICES)) * 100)

    @property
    def is_delayed(self):
        if self.status == 'ACQUISITION_COMPLETED':
            return False
        if self.target_completion_date and self.target_completion_date < timezone.now().date():
            return True
        return False

    @property
    def pending_area_acres(self):
        pending = self.required_area_acres - self.acquired_area_acres
        return max(pending, 0)


class StatusHistory(models.Model):
    """Immutable log of every status transition and exception for a project or land parcel."""

    project = models.ForeignKey(AcquisitionProject, on_delete=models.CASCADE, related_name='status_history')
    land_record = models.ForeignKey(
        'land_records.LandRecord',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='status_history',
    )
    previous_status = models.CharField(max_length=35, choices=ACQUISITION_STATUS_CHOICES, blank=True)
    status = models.CharField(max_length=35, choices=ACQUISITION_STATUS_CHOICES)
    remarks = models.TextField(blank=True)
    is_exception = models.BooleanField(default=False)
    exception_reason = models.TextField(blank=True)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='status_updates',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.project.project_code}: {self.get_status_display()}"


class Document(models.Model):
    """Official documents attached to projects or land records."""

    DOCUMENT_TYPES = [
        ('NOTIFICATION', 'Official Notification'),
        ('SURVEY_MAP', 'Survey Map / Sketch'),
        ('LAND_TITLE', 'Land Title / 7-12 Extract'),
        ('VALUATION', 'Valuation Report'),
        ('POSSESSION', 'Possession Certificate'),
        ('OTHER', 'Other Official Document'),
    ]

    title = models.CharField(max_length=200)
    document_type = models.CharField(max_length=30, choices=DOCUMENT_TYPES, default='OTHER')
    file = models.FileField(upload_to='documents/%Y/%m/', validators=[validate_document_file])
    project = models.ForeignKey(
        AcquisitionProject,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='documents',
    )
    land_record = models.ForeignKey(
        'land_records.LandRecord',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='documents',
    )
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='uploaded_documents',
    )
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title
