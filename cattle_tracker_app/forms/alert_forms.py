from __future__ import annotations

from django import forms
from cattle_tracker_app.models import AlertRule


class AlertRuleForm(forms.ModelForm):
    class Meta:
        model = AlertRule
        fields = ["owner", "alert_type", "lead_days", "enabled", "in_app", "email", "sms"]

    def __init__(self, *args, allowed_owners=None, **kwargs):
        super().__init__(*args, **kwargs)
        if allowed_owners is not None:
            self.fields["owner"].queryset = allowed_owners