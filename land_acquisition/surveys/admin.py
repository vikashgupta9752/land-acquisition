from django.contrib import admin
from .models import SurveyAssignment, SurveyReport


@admin.register(SurveyAssignment)
class SurveyAssignmentAdmin(admin.ModelAdmin):
    list_display = ('id', 'land_record', 'project', 'surveyor', 'status', 'assigned_date', 'due_date')
    list_filter = ('status', 'project')


@admin.register(SurveyReport)
class SurveyReportAdmin(admin.ModelAdmin):
    list_display = ('assignment', 'actual_area_acres', 'verified_land_type', 'inspection_date', 'verified_by')
