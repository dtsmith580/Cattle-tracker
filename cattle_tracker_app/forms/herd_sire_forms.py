# forms/herd_sire_forms.py
from django import forms
from cattle_tracker_app.models.herd_sire_models import HerdSire

class HerdSireForm(forms.ModelForm):
    class Meta:
        model = HerdSire
        fields = '__all__'
        widgets = {
            'notes': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
            'profile_link': forms.URLInput(attrs={'class': 'form-control'}),
        }
