from django.contrib import admin
from .models import Landowner, LandRecord, PossessionRecord


@admin.register(Landowner)
class LandownerAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'phone', 'village', 'district', 'user')
    search_fields = ('full_name', 'phone', 'village', 'district')


@admin.register(LandRecord)
class LandRecordAdmin(admin.ModelAdmin):
    list_display = ('survey_number', 'plot_number', 'project', 'landowner', 'area_acres', 'acquisition_status', 'is_acquired')
    list_filter = ('acquisition_status', 'land_type', 'is_acquired', 'district')
    search_fields = ('survey_number', 'plot_number', 'village', 'landowner__full_name')


@admin.register(PossessionRecord)
class PossessionRecordAdmin(admin.ModelAdmin):
    list_display = ('land_record', 'project', 'possession_date', 'status', 'handover_officer')
    list_filter = ('status',)
