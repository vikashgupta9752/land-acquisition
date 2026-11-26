from django.conf import settings
from django.db import models
from projects.constants import ACQUISITION_STATUS_CHOICES, STATUS_BADGE_MAP, STATUS_ORDER
from projects.validators import validate_document_file


class Landowner(models.Model):
    """Citizen or entity owning land affected by an acquisition project."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='landowner_profile',
    )
    full_name = models.CharField(max_length=150)
    father_or_spouse_name = models.CharField(max_length=150, blank=True)
    aadhaar_last4 = models.CharField(max_length=4, blank=True, help_text='Last 4 digits of Aadhaar for verification')
    phone = models.CharField(max_length=20)
    email = models.EmailField(blank=True)
    address = models.TextField()
    village = models.CharField(max_length=120)
    district = models.CharField(max_length=100)
    bank_account_number = models.CharField(max_length=40, blank=True)
    ifsc_code = models.CharField(max_length=20, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['full_name']

    def __str__(self):
        return f"{self.full_name} ({self.village}, {self.district})"


class LandRecord(models.Model):
    """Individual land parcel registered under an acquisition project."""

    LAND_TYPES = [
        ('AGRICULTURAL', 'Agricultural'),
        ('RESIDENTIAL', 'Residential'),
        ('COMMERCIAL', 'Commercial'),
        ('INDUSTRIAL', 'Industrial'),
        ('BARREN', 'Barren / Waste Land'),
        ('FOREST', 'Forest / Green Cover'),
    ]

    OWNERSHIP_TYPES = [
        ('SOLE', 'Sole Ownership'),
        ('JOINT', 'Joint Ownership'),
        ('LEASE', 'Leasehold'),
        ('GOVERNMENT', 'Government / Trust'),
    ]

    POSSESSION_STATUSES = [
        ('PENDING', 'Pending'),
        ('NOTICE_ISSUED', 'Notice Issued'),
        ('TAKEN_OVER', 'Possession Taken Over'),
    ]

    project = models.ForeignKey(
        'projects.AcquisitionProject',
        on_delete=models.CASCADE,
        related_name='land_records',
    )
    landowner = models.ForeignKey(Landowner, on_delete=models.PROTECT, related_name='land_records')
    survey_number = models.CharField(max_length=60)
    plot_number = models.CharField(max_length=60)
    khata_number = models.CharField(max_length=60, blank=True)
    village = models.CharField(max_length=120)
    taluka = models.CharField(max_length=100, blank=True)
    district = models.CharField(max_length=100)
    area_acres = models.DecimalField(max_digits=10, decimal_places=2)
    land_type = models.CharField(max_length=20, choices=LAND_TYPES, default='AGRICULTURAL')
    ownership_type = models.CharField(max_length=20, choices=OWNERSHIP_TYPES, default='SOLE')
    current_usage = models.CharField(max_length=200, blank=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    boundary_geojson = models.TextField(blank=True)
    acquisition_status = models.CharField(
        max_length=35,
        choices=ACQUISITION_STATUS_CHOICES,
        default='LAND_REGISTERED',
    )
    possession_status = models.CharField(max_length=20, choices=POSSESSION_STATUSES, default='PENDING')
    is_acquired = models.BooleanField(default=False)
    remarks = models.TextField(blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_land_records',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        unique_together = [('project', 'survey_number', 'plot_number')]

    def __str__(self):
        return f"Survey {self.survey_number} / Plot {self.plot_number} ({self.village})"

    @property
    def status_badge(self):
        return STATUS_BADGE_MAP.get(self.acquisition_status, 'secondary')

    @property
    def progress_percent(self):
        step = STATUS_ORDER.get(self.acquisition_status, 1)
        return round((step / len(ACQUISITION_STATUS_CHOICES)) * 100)


class PossessionRecord(models.Model):
    """Formal land possession handover record."""

    POSSESSION_STATES = [
        ('PENDING', 'Pending'),
        ('SCHEDULED', 'Scheduled'),
        ('COMPLETED', 'Completed'),
    ]

    land_record = models.OneToOneField(LandRecord, on_delete=models.CASCADE, related_name='possession_record')
    project = models.ForeignKey(
        'projects.AcquisitionProject',
        on_delete=models.CASCADE,
        related_name='possession_records',
    )
    possession_date = models.DateField()
    handover_officer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='handovers',
    )
    witness_names = models.CharField(max_length=255, blank=True)
    remarks = models.TextField(blank=True)
    possession_document = models.FileField(
        upload_to='possession/%Y/%m/',
        null=True,
        blank=True,
        validators=[validate_document_file],
    )
    status = models.CharField(max_length=20, choices=POSSESSION_STATES, default='COMPLETED')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Possession: {self.land_record} ({self.get_status_display()})"
