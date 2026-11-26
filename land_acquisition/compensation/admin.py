from django.contrib import admin
from .models import Compensation, Payment


@admin.register(Compensation)
class CompensationAdmin(admin.ModelAdmin):
    list_display = ('land_record', 'project', 'base_land_value', 'proposed_compensation', 'approved_compensation', 'status')
    list_filter = ('status', 'project')


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('landowner', 'compensation', 'amount', 'payment_mode', 'status', 'payment_date')
    list_filter = ('status', 'payment_mode')
