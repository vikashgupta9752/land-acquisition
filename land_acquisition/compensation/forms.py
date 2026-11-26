from django import forms
from land_records.models import LandRecord
from .models import Compensation, Payment


class CompensationCalculatorForm(forms.ModelForm):
    class Meta:
        model = Compensation
        fields = [
            'land_record', 'land_area_acres', 'rate_per_acre',
            'solatium_percent', 'structure_compensation', 'tree_crop_compensation',
            'interest_amount', 'other_allowance', 'valuation_remarks',
        ]
        widgets = {
            'land_record': forms.Select(attrs={'class': 'form-select'}),
            'land_area_acres': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'id': 'id_land_area_acres'}),
            'rate_per_acre': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'id': 'id_rate_per_acre'}),
            'solatium_percent': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'id': 'id_solatium_percent'}),
            'structure_compensation': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'id': 'id_structure_compensation'}),
            'tree_crop_compensation': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'id': 'id_tree_crop_compensation'}),
            'interest_amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'id': 'id_interest_amount'}),
            'other_allowance': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'id': 'id_other_allowance'}),
            'valuation_remarks': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['land_record'].queryset = LandRecord.objects.select_related('project', 'landowner')


class CompensationApprovalForm(forms.Form):
    approved_compensation = forms.DecimalField(
        max_digits=16,
        decimal_places=2,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
    )
    valuation_remarks = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
    )


class PaymentForm(forms.ModelForm):
    class Meta:
        model = Payment
        fields = [
            'amount', 'payment_mode', 'transaction_reference',
            'payment_date', 'status', 'receipt_document', 'remarks',
        ]
        widgets = {
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'payment_mode': forms.Select(attrs={'class': 'form-select'}),
            'transaction_reference': forms.TextInput(attrs={'class': 'form-control'}),
            'payment_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'receipt_document': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'remarks': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }
