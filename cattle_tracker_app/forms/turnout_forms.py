# cattle_tracker_app/forms/turnout_forms.py
from django import forms
from django.utils import timezone
from dateutil.relativedelta import relativedelta
from cattle_tracker_app.models import TurnoutGroup, Cattle
from cattle_tracker_app.utils.access import get_user_allowed_owner_ids

class TurnoutGroupForm(forms.ModelForm):
    class Meta:
        model = TurnoutGroup
        fields = ["name", "bulls", "cows", "turn_in_date", "turn_out_date"]

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)

        today = timezone.now().date()
        cutoff_cows = today - relativedelta(months=14)
        cutoff_bulls = today - relativedelta(months=16)

        bulls_qs = Cattle.objects.filter(
            animal_type="Bull",
            dob__lte=cutoff_bulls,
        ).exclude(status__in=["dead", "sold"])

        cows_qs = Cattle.objects.filter(
            animal_type__in=["Cow", "Heifer"],
            dob__lte=cutoff_cows,
        ).exclude(status__in=["dead", "sold"])

        if user and user.is_authenticated:
            allowed_owner_ids = list(get_user_allowed_owner_ids(user))
            if allowed_owner_ids:
                bulls_qs = bulls_qs.filter(owner_id__in=allowed_owner_ids)
                cows_qs = cows_qs.filter(owner_id__in=allowed_owner_ids)
            else:
                bulls_qs = bulls_qs.none()
                cows_qs = cows_qs.none()

        # 🔐 Include already-selected animals so they remain visible on edit
        if self.instance and self.instance.pk:
            bulls_qs = (bulls_qs | self.instance.bulls.all()).distinct()
            cows_qs = (cows_qs | self.instance.cows.all()).distinct()

        self.fields["bulls"].queryset = bulls_qs.order_by("ear_tag", "id")
        self.fields["cows"].queryset  = cows_qs.order_by("ear_tag", "id")
