from django import forms
from django.db.models import Q
from cattle_tracker_app.models.herd_bull_models import HerdBull
from cattle_tracker_app.models.cattle_models import Cattle  # your hub import

class HerdBullForm(forms.ModelForm):
    class Meta:
        model = HerdBull
        fields = [
            "cattle",
            "fertility_test_date", "fertility_status",
            "scrotal_circumference_cm", "frame_score",
            "semen_collected", "semen_straws_on_hand", "semen_storage_location",
            "epd_profile_url", "notes",
        ]

    def __init__(self, *args, request=None, **kwargs):
        super().__init__(*args, **kwargs)

        base_qs = (Cattle.objects
                   .filter(animal_type__iexact="bull")
                   .exclude(status__iexact="sold")
                   .exclude(status__iexact="dead"))

        # Owner scoping (only if helper returns a non-empty list)
        owner_ids = None
        if request and hasattr(request, "user"):
            try:
                from cattle_tracker_app.utils.access import get_user_allowed_owners
                owner_ids = list(get_user_allowed_owners(request.user).values_list("id", flat=True))
            except Exception:
                owner_ids = None

        # CREATE mode: show bulls without a HerdBull profile
        if not self.instance or not self.instance.pk:
            qs = base_qs.filter(herd_bull_profile__isnull=True)
            if owner_ids:
                qs = qs.filter(owner_id__in=owner_ids)
            self.fields["cattle"].queryset = qs.order_by("owner__name", "ear_tag")
        else:
            # EDIT mode: always include the currently selected bull
            current_pk = self.instance.cattle_id
            qs = base_qs.filter(
                Q(herd_bull_profile__isnull=True) | Q(pk=current_pk)
            )
            if owner_ids:
                qs = qs.filter(Q(owner_id__in=owner_ids) | Q(pk=current_pk))

            self.fields["cattle"].queryset = qs.order_by("owner__name", "ear_tag")

            # Make the association read-only in the UI (keeps data from changing)
            self.fields["cattle"].disabled = True