# cattle_tracker_app/forms/settings_forms.py

from django import forms
from cattle_tracker_app.models.settings_models import RanchSetting

class RanchSettingForm(forms.ModelForm):
    class Meta:
        model = RanchSetting
        fields = ['backup_frequency_hours','name', 'mailing_address', 'phone', 'email']
        widgets = {
            'backup_frequency_hours': forms.NumberInput(attrs={"min": 1, "step": 1}),
            'mailing_address': forms.Textarea(attrs={
                'rows': 3,
                'placeholder': 'e.g., 5306 Roadrunner Dr, Durant, OK 74701'
            }),
        }
