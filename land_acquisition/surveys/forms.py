from django import forms
from django.contrib.auth.models import User
from land_records.models import LandRecord
from .models import SurveyAssignment, SurveyReport


class SurveyAssignmentForm(forms.ModelForm):
    class Meta:
        model = SurveyAssignment
        fields = ['land_record', 'surveyor', 'due_date', 'instructions']
        widgets = {
            'land_record': forms.Select(attrs={'class': 'form-select'}),
            'surveyor': forms.Select(attrs={'class': 'form-select'}),
            'due_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'instructions': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['surveyor'].queryset = User.objects.filter(
            profile__role='SURVEYOR', is_active=True
        )
        self.fields['land_record'].queryset = LandRecord.objects.select_related('project', 'landowner')


class SurveyReportForm(forms.ModelForm):
    class Meta:
        model = SurveyReport
        fields = [
            'actual_area_acres', 'verified_land_type', 'current_land_usage',
            'boundary_verified', 'encroachment_found', 'structures_present',
            'trees_crops_details', 'inspection_date', 'inspection_remarks',
            'photo_1', 'photo_2', 'report_document',
        ]
        widgets = {
            'actual_area_acres': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'verified_land_type': forms.TextInput(attrs={'class': 'form-control'}),
            'current_land_usage': forms.TextInput(attrs={'class': 'form-control'}),
            'boundary_verified': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'encroachment_found': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'structures_present': forms.TextInput(attrs={'class': 'form-control'}),
            'trees_crops_details': forms.TextInput(attrs={'class': 'form-control'}),
            'inspection_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'inspection_remarks': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'photo_1': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'photo_2': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'report_document': forms.ClearableFileInput(attrs={'class': 'form-control'}),
        }
