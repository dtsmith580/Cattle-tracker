# forms/pasture_forms.py
from django import forms
import json
from cattle_tracker_app.models import Paddock
from cattle_tracker_app.models.pasture_models import Pasture

class PaddockForm(forms.ModelForm):
    # Optional: let normal (non-AJAX) forms pass GeoJSON. You can render this as hidden in templates.
    boundary = forms.CharField(required=False, widget=forms.Textarea(attrs={'rows': 3}))

    class Meta:
        model = Paddock
        # We exclude 'acres' from editable fields since it’s computed server-side.
        fields = ['name', 'pasture', 'boundary']  # keep pasture; acres computed on save via view

    def __init__(self, *args, **kwargs):
        pasture_instance = kwargs.pop('pasture', None)
        super().__init__(*args, **kwargs)

        # If you want acres to show but not be editable, uncomment:
        # self.fields['acres'] = forms.DecimalField(
        #     required=False, disabled=True, label="Acres (auto)",
        #     widget=forms.NumberInput(attrs={'readonly': 'readonly'})
        # )

        if pasture_instance:
            self.fields['pasture'].initial = pasture_instance
            self.fields['pasture'].widget = forms.HiddenInput()

    def clean_boundary(self):
        """Normalize boundary to a dict if user pasted JSON (for non-AJAX form flows)."""
        b = self.cleaned_data.get('boundary')
        if not b:
            return None
        if isinstance(b, dict):
            return b
        try:
            return json.loads(b)
        except Exception:
            raise forms.ValidationError("Boundary must be valid GeoJSON (Geometry, Feature, or FeatureCollection).")


class PastureForm(forms.ModelForm):
    class Meta:
        model = Pasture
        fields = ['name', 'size_acres', 'water_source_type', 'water_quantity_gallons', 'location_description', 'is_active']
        widgets = {
            'location_description': forms.Textarea(attrs={'rows': 2}),
        }
