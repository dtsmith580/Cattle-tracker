from django import forms
from cattle_tracker_app.models.weight_models import WeightLog


class WeightLogForm(forms.ModelForm):
    labels = {
        'date': 'Weigh Date',
        'weight': 'Weight (lbs)',
        'notes': 'Notes (optional)',
    }
    class Meta:
        model = WeightLog
        fields = ['date', 'weight', 'notes']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
            'weight': forms.NumberInput(attrs={'step': '0.01'}),
            'notes': forms.Textarea(attrs={'rows': 2}),
        }
