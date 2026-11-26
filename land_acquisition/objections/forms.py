from django import forms
from land_records.models import LandRecord
from .models import Objection


class ObjectionSubmitForm(forms.ModelForm):
    class Meta:
        model = Objection
        fields = ['land_record', 'subject', 'category', 'description', 'supporting_document']
        widgets = {
            'land_record': forms.Select(attrs={'class': 'form-select'}),
            'subject': forms.TextInput(attrs={'class': 'form-control'}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'supporting_document': forms.ClearableFileInput(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, landowner=None, **kwargs):
        super().__init__(*args, **kwargs)
        if landowner is not None:
            self.fields['land_record'].queryset = LandRecord.objects.filter(landowner=landowner)


class ObjectionReviewForm(forms.Form):
    status = forms.ChoiceField(
        choices=[
            ('UNDER_REVIEW', 'Under Review'),
            ('APPROVED', 'Approved'),
            ('REJECTED', 'Rejected'),
        ],
        widget=forms.Select(attrs={'class': 'form-select'}),
    )
    officer_remarks = forms.CharField(
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
    )
