from django import forms
from .models import Landowner, LandRecord, PossessionRecord


class LandownerForm(forms.ModelForm):
    class Meta:
        model = Landowner
        fields = [
            'full_name', 'father_or_spouse_name', 'aadhaar_last4', 'phone', 'email',
            'address', 'village', 'district', 'bank_account_number', 'ifsc_code',
        ]
        widgets = {
            'full_name': forms.TextInput(attrs={'class': 'form-control'}),
            'father_or_spouse_name': forms.TextInput(attrs={'class': 'form-control'}),
            'aadhaar_last4': forms.TextInput(attrs={'class': 'form-control', 'maxlength': 4}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'village': forms.TextInput(attrs={'class': 'form-control'}),
            'district': forms.TextInput(attrs={'class': 'form-control'}),
            'bank_account_number': forms.TextInput(attrs={'class': 'form-control'}),
            'ifsc_code': forms.TextInput(attrs={'class': 'form-control'}),
        }


class LandRecordForm(forms.ModelForm):
    class Meta:
        model = LandRecord
        fields = [
            'project', 'landowner', 'survey_number', 'plot_number', 'khata_number',
            'village', 'taluka', 'district', 'area_acres', 'land_type',
            'ownership_type', 'current_usage', 'latitude', 'longitude',
            'boundary_geojson', 'remarks',
        ]
        widgets = {
            'project': forms.Select(attrs={'class': 'form-select'}),
            'landowner': forms.Select(attrs={'class': 'form-select'}),
            'survey_number': forms.TextInput(attrs={'class': 'form-control'}),
            'plot_number': forms.TextInput(attrs={'class': 'form-control'}),
            'khata_number': forms.TextInput(attrs={'class': 'form-control'}),
            'village': forms.TextInput(attrs={'class': 'form-control'}),
            'taluka': forms.TextInput(attrs={'class': 'form-control'}),
            'district': forms.TextInput(attrs={'class': 'form-control'}),
            'area_acres': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'land_type': forms.Select(attrs={'class': 'form-select'}),
            'ownership_type': forms.Select(attrs={'class': 'form-select'}),
            'current_usage': forms.TextInput(attrs={'class': 'form-control'}),
            'latitude': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.000001'}),
            'longitude': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.000001'}),
            'boundary_geojson': forms.HiddenInput(),
            'remarks': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }


class PossessionRecordForm(forms.ModelForm):
    mark_acquisition_completed = forms.BooleanField(
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        label='Mark land parcel acquisition as fully completed',
    )

    class Meta:
        model = PossessionRecord
        fields = ['possession_date', 'witness_names', 'possession_document', 'remarks']
        widgets = {
            'possession_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'witness_names': forms.TextInput(attrs={'class': 'form-control'}),
            'possession_document': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'remarks': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }
