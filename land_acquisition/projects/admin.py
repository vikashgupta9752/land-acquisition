from django.contrib import admin
from .models import AcquisitionProject, Department, Document, StatusHistory


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'head_name', 'contact_email')
    search_fields = ('name', 'code')


@admin.register(AcquisitionProject)
class AcquisitionProjectAdmin(admin.ModelAdmin):
    list_display = ('project_code', 'name', 'department', 'district', 'village', 'status', 'assigned_officer')
    list_filter = ('status', 'department', 'district')
    search_fields = ('project_code', 'name', 'village', 'district')


@admin.register(StatusHistory)
class StatusHistoryAdmin(admin.ModelAdmin):
    list_display = ('project', 'land_record', 'status', 'is_exception', 'updated_by', 'created_at')
    list_filter = ('status', 'is_exception')


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ('title', 'document_type', 'project', 'uploaded_by', 'created_at')
    list_filter = ('document_type',)
