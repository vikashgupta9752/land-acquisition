from decimal import Decimal
from django.conf import settings
from django.db import models
from projects.validators import validate_document_file


class Compensation(models.Model):
    """Valuation and compensation record for a land parcel."""

    COMPENSATION_STATUSES = [
        ('ESTIMATED', 'Estimated'),
        ('PROPOSED', 'Proposed'),
        ('APPROVED', 'Approved'),
        ('DISBURSED', 'Disbursed'),
    ]

    land_record = models.OneToOneField(
        'land_records.LandRecord',
        on_delete=models.CASCADE,
        related_name='compensation',
    )
    project = models.ForeignKey(
        'projects.AcquisitionProject',
        on_delete=models.CASCADE,
        related_name='compensations',
    )
    land_area_acres = models.DecimalField(max_digits=10, decimal_places=2)
    rate_per_acre = models.DecimalField(max_digits=14, decimal_places=2)
    base_land_value = models.DecimalField(max_digits=16, decimal_places=2, default=0)
    solatium_percent = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('100.00'))
    solatium_amount = models.DecimalField(max_digits=16, decimal_places=2, default=0)
    structure_compensation = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    tree_crop_compensation = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    interest_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    other_allowance = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    additional_compensation = models.DecimalField(max_digits=16, decimal_places=2, default=0)
    proposed_compensation = models.DecimalField(max_digits=16, decimal_places=2, default=0)
    approved_compensation = models.DecimalField(max_digits=16, decimal_places=2, null=True, blank=True)
    valuation_remarks = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=COMPENSATION_STATUSES, default='PROPOSED')
    calculated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='calculated_compensations',
    )
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_compensations',
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def recalculate(self):
        """Compute base, additional, and final proposed compensation."""
        self.base_land_value = (self.land_area_acres * self.rate_per_acre).quantize(Decimal('0.01'))
        self.solatium_amount = (
            self.base_land_value * (self.solatium_percent / Decimal('100.00'))
        ).quantize(Decimal('0.01'))
        self.additional_compensation = (
            self.solatium_amount
            + self.structure_compensation
            + self.tree_crop_compensation
            + self.interest_amount
            + self.other_allowance
        ).quantize(Decimal('0.01'))
        self.proposed_compensation = (self.base_land_value + self.additional_compensation).quantize(Decimal('0.01'))

    def save(self, *args, **kwargs):
        self.recalculate()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Compensation for {self.land_record} - ₹{self.proposed_compensation:,.2f}"


class Payment(models.Model):
    """Payment disbursement record for approved compensation."""

    PAYMENT_STATUSES = [
        ('PENDING', 'Pending'),
        ('PROCESSING', 'Processing'),
        ('PAID', 'Paid'),
        ('FAILED', 'Failed'),
    ]

    PAYMENT_MODES = [
        ('NEFT', 'NEFT'),
        ('RTGS', 'RTGS'),
        ('DBT', 'Direct Benefit Transfer (DBT)'),
        ('CHEQUE', 'Account Payee Cheque'),
    ]

    compensation = models.ForeignKey(Compensation, on_delete=models.CASCADE, related_name='payments')
    landowner = models.ForeignKey(
        'land_records.Landowner',
        on_delete=models.PROTECT,
        related_name='payments',
    )
    transaction_reference = models.CharField(max_length=80, blank=True)
    amount = models.DecimalField(max_digits=16, decimal_places=2)
    payment_mode = models.CharField(max_length=20, choices=PAYMENT_MODES, default='DBT')
    payment_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=PAYMENT_STATUSES, default='PENDING')
    remarks = models.TextField(blank=True)
    processed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='processed_payments',
    )
    receipt_document = models.FileField(
        upload_to='payments/receipts/%Y/%m/',
        null=True,
        blank=True,
        validators=[validate_document_file],
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Payment ₹{self.amount:,.2f} to {self.landowner.full_name} ({self.get_status_display()})"

    @property
    def status_badge(self):
        return {
            'PENDING': 'warning',
            'PROCESSING': 'info',
            'PAID': 'success',
            'FAILED': 'danger',
        }.get(self.status, 'secondary')
