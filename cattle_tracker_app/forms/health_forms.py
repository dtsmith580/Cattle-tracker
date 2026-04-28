# cattle_tracker_app/forms/health_forms.py
from django import forms
from django.db import transaction
from django.forms import modelformset_factory

from ..models import HealthRecord, VaccinationRecord, CastrationRecord, Cattle
from ..models.ownership_models import get_user_allowed_owners


class HealthRecordForm(forms.ModelForm):
    """
    Back-compat + multi-vaccine support:
    - Keep single-vaccine "extra fields" (for existing pages).
    - When a view passes use_vax_formset=True, we DO NOT create/update vaccination rows here.
      The view will save a VaccinationRecord formset (0..N rows) tied to this HealthRecord.
    """

    # Single-vaccine extras (optional; used by older pages)
    vaccine_name = forms.CharField(max_length=100, required=False)
    dose = forms.CharField(max_length=50, required=False)
    administration_method = forms.CharField(max_length=50, required=False)
    batch_number = forms.CharField(max_length=50, required=False)
    withdrawal_date = forms.DateField(required=False, widget=forms.DateInput(attrs={'type': 'date'}))

    # Castration extras (optional)
    method = forms.ChoiceField(choices=[('', '---------')] + list(CastrationRecord.METHOD_CHOICES), required=False)
    age_days = forms.IntegerField(required=False, min_value=0)
    complications = forms.CharField(required=False, widget=forms.Textarea(attrs={'rows': 2}))

    class Meta:
        model = HealthRecord
        fields = [
            'cattle', 'date', 'event_type', 'title', 'description',
            'performed_by', 'cost', 'next_due', 'attachment',
        ]
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
            'next_due': forms.DateInput(attrs={'type': 'date'}),
            'description': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        # New flag: when True, vaccines are handled via formset (0..N)
        self.use_vax_formset = kwargs.pop('use_vax_formset', False)
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)

        # Filter cattle queryset: by owner access and exclude sold/dead
        qs = Cattle.objects.all()
        if self.request and self.request.user.is_authenticated:
            allowed_owners = get_user_allowed_owners(self.request.user)
            qs = qs.filter(owner__in=allowed_owners)
        qs = qs.exclude(status__in=['sold', 'dead'])
        self.fields['cattle'].queryset = qs.order_by('owner__name', 'ear_tag')

    def clean(self):
        cleaned = super().clean()
        etype = cleaned.get('event_type')

        # If this form is NOT using a formset, enforce single-vaccine requirement on vaccination.
        if not self.use_vax_formset and etype == HealthRecord.EventType.VACCINATION:
            if not cleaned.get('vaccine_name'):
                self.add_error('vaccine_name', "Vaccine name is required for vaccination records.")

        # (No extra rules needed for illness here; multi-vax handled in the view via formset.)
        return cleaned

    @transaction.atomic
    def save(self, commit=True):
        record = super().save(commit)
        etype = self.cleaned_data.get('event_type')

        if self.use_vax_formset:
            # When using the multi-vax formset:
            # - For CASRATION: keep castration upsert and clear any vaccines.
            # - For VACCINATION or ILLNESS: do NOT touch VaccinationRecord here (view will save them).
            # - For others: leave vaccines as-is; clear castration.
            if etype == HealthRecord.EventType.CASTRATION:
                vals = {
                    'method': self.cleaned_data.get('method') or '',
                    'age_days': self.cleaned_data.get('age_days') or None,
                    'complications': self.cleaned_data.get('complications') or '',
                }
                CastrationRecord.objects.update_or_create(health_record=record, defaults=vals)
                VaccinationRecord.objects.filter(health_record=record).delete()
            else:
                # Not a castration event -> ensure no stray castration detail
                CastrationRecord.objects.filter(health_record=record).delete()
            return record

        # ========= Legacy single-vaccine behavior (no formset in the view) =========
        if etype == HealthRecord.EventType.VACCINATION:
            vals = {
                'vaccine_name': self.cleaned_data.get('vaccine_name', ''),
                'dose': self.cleaned_data.get('dose', ''),
                'administration_method': self.cleaned_data.get('administration_method', ''),
                'batch_number': self.cleaned_data.get('batch_number', ''),
                'withdrawal_date': self.cleaned_data.get('withdrawal_date', None),
            }
            # Upsert a single vaccine tied to this health record
            VaccinationRecord.objects.update_or_create(health_record=record, defaults=vals)
            CastrationRecord.objects.filter(health_record=record).delete()

        elif etype == HealthRecord.EventType.CASTRATION:
            vals = {
                'method': self.cleaned_data.get('method') or '',
                'age_days': self.cleaned_data.get('age_days') or None,
                'complications': self.cleaned_data.get('complications') or '',
            }
            CastrationRecord.objects.update_or_create(health_record=record, defaults=vals)
            VaccinationRecord.objects.filter(health_record=record).delete()

        else:
            # Neither vaccination nor castration -> ensure no stray detail records
            VaccinationRecord.objects.filter(health_record=record).delete()
            CastrationRecord.objects.filter(health_record=record).delete()

        return record


# === Multi-vaccine support ===
class VaccinationRecordForm(forms.ModelForm):
    class Meta:
        model = VaccinationRecord
        fields = ['vaccine_name', 'dose', 'administration_method', 'batch_number', 'withdrawal_date']
        widgets = {
            'withdrawal_date': forms.DateInput(attrs={'type': 'date'}),
        }

# 0..N vaccines; we’ll attach them to the HealthRecord in the view
VaccinationFormSet = modelformset_factory(
    VaccinationRecord,
    form=VaccinationRecordForm,
    extra=1,
    can_delete=True
)


class HerdVaccinationForm(forms.Form):
    """
    Bulk apply the same vaccination to many animals.
    """
    cattle = forms.ModelMultipleChoiceField(
        queryset=Cattle.objects.none(),
        widget=forms.SelectMultiple(attrs={'class': 'select2', 'size': 12})
    )
    date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}))
    vaccine_name = forms.CharField(max_length=100)
    dose = forms.CharField(max_length=50, required=False)
    administration_method = forms.CharField(max_length=50, required=False)
    batch_number = forms.CharField(max_length=50, required=False)
    withdrawal_date = forms.DateField(required=False, widget=forms.DateInput(attrs={'type': 'date'}))
    next_due = forms.DateField(required=False, widget=forms.DateInput(attrs={'type': 'date'}))
    performed_by = forms.CharField(max_length=100, required=False)
    cost = forms.DecimalField(required=False, max_digits=10, decimal_places=2)

    def __init__(self, *args, **kwargs):
        request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)
        qs = Cattle.objects.all()
        if request and request.user.is_authenticated:
            allowed_owners = get_user_allowed_owners(request.user)
            qs = qs.filter(owner__in=allowed_owners)
        qs = qs.exclude(status__in=['sold', 'dead']).order_by('owner__name', 'ear_tag')
        self.fields['cattle'].queryset = qs
