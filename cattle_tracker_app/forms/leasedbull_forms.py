from django import forms
from cattle_tracker_app.models import LeasedBull

class LeasedBullForm(forms.ModelForm):
    class Meta:
        model = LeasedBull
        fields = ['ear_tag', 'breed', 'dob', 'owner_name', 'lease_start', 'lease_end', 'image']
        widgets = {
            'ear_tag': forms.TextInput(attrs={'class': 'w-full rounded border-gray-300'}),
            'breed': forms.TextInput(attrs={'class': 'w-full rounded border-gray-300'}),
            'dob': forms.DateInput(attrs={'type': 'date', 'class': 'w-full rounded border-gray-300'}),
            'lease_start': forms.DateInput(attrs={'type': 'date', 'class': 'w-full rounded border-gray-300'}),
            'lease_end': forms.DateInput(attrs={'type': 'date', 'class': 'w-full rounded border-gray-300'}),
        }