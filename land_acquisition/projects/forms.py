from django import forms
from django.contrib.auth.models import User
from notifications.models import Notification
from projects.constants import ACQUISITION_STATUS_CHOICES
from .models import AcquisitionProject, Department, Document


class DepartmentForm(forms.ModelForm):
    class Meta:
        model = Department
        fields = ['name', 'code', 'head_name', 'contact_email', 'description']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'code': forms.TextInput(attrs={'class': 'form-control'}),
            'head_name': forms.TextInput(attrs={'class': 'form-control'}),
            'contact_email': forms.EmailInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }


class AcquisitionProjectForm(forms.ModelForm):
    class Meta:
        model = AcquisitionProject
        fields = [
            'project_code', 'name', 'purpose', 'department', 'assigned_officer',
            'state', 'district', 'taluka', 'village', 'required_area_acres',
            'latitude', 'longitude', 'boundary_geojson',
            'start_date', 'target_completion_date', 'description',
        ]
        widgets = {
            'project_code': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., NHAI-2026-001'}),
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'purpose': forms.TextInput(attrs={'class': 'form-control'}),
            'department': forms.Select(attrs={'class': 'form-select'}),
            'assigned_officer': forms.Select(attrs={'class': 'form-select'}),
            'state': forms.TextInput(attrs={'class': 'form-control'}),
            'district': forms.TextInput(attrs={'class': 'form-control'}),
            'taluka': forms.TextInput(attrs={'class': 'form-control'}),
            'village': forms.TextInput(attrs={'class': 'form-control'}),
            'required_area_acres': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'latitude': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.000001'}),
            'longitude': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.000001'}),
            'boundary_geojson': forms.HiddenInput(),
            'start_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'target_completion_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['assigned_officer'].queryset = User.objects.filter(
            profile__role='OFFICER', is_active=True
        )


class ProjectStatusExceptionForm(forms.Form):
    """Allows authorized officers to update status or record an exception with reason."""

    status = forms.ChoiceField(
        choices=ACQUISITION_STATUS_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'}),
    )
    remarks = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
    )
    is_exception = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        label='Mark as workflow exception (non-standard timeline)',
    )
    exception_reason = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
    )


class DocumentUploadForm(forms.ModelForm):
    class Meta:
        model = Document
        fields = ['title', 'document_type', 'file', 'description']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'document_type': forms.Select(attrs={'class': 'form-select'}),
            'file': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }


class OfficialNotificationForm(forms.ModelForm):
    class Meta:
        model = Notification
        fields = ['notice_number', 'title', 'message', 'attachment']
        widgets = {
            'notice_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., SEC-4/2026/101'}),
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'message': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'attachment': forms.ClearableFileInput(attrs={'class': 'form-control'}),
        }
