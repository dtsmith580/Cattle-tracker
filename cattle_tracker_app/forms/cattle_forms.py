# cattle_tracker_app/forms/cattle_forms.py
# Production-ready CattleForm with:
#  - Owner-filtered paddock queryset
#  - Breadcrumb labels: Property → Pasture → Paddock
#  - Robust dynamic model resolution (no NameError on HerdSire/LeasedBull)
#  - Validation: leased bull requirement + paddock access guard

from datetime import date
from dateutil.relativedelta import relativedelta
from django import forms
from django.apps import apps
from django.core.exceptions import ValidationError

# Prefer dynamic access helper; fall back to OwnerUserAccess
try:
    from cattle_tracker_app.utils.access import get_user_allowed_owners  # type: ignore
except Exception:  # pragma: no cover
    def get_user_allowed_owners(user):
        from cattle_tracker_app.models.ownership_models import OwnerUserAccess
        return list(OwnerUserAccess.objects.filter(user=user).values_list('owner_id', flat=True))

# Import Cattle explicitly for ModelForm Meta
from cattle_tracker_app.models.cattle_models import Cattle


class CattleForm(forms.ModelForm):
    class Meta:
        model = Cattle
        fields = "__all__"
        widgets = {
            "dob": forms.DateInput(attrs={"type": "date"}),
            "paddock": forms.Select(attrs={"class": "form-select"}),
            # "image": forms.ClearableFileInput(attrs={"class": "form-control"}),  # if you have it
        }

    def __init__(self, *args, **kwargs):
        # Accept user & context for filtering and behavior toggles
        self._user = kwargs.pop("user", None)
        self._context = kwargs.pop("context", None)
        super().__init__(*args, **kwargs)

        # Resolve models dynamically to avoid circular imports / NameError
        Paddock = apps.get_model("cattle_tracker_app", "Paddock")
        Pasture = apps.get_model("cattle_tracker_app", "Pasture")
        CattleModel = apps.get_model("cattle_tracker_app", "Cattle")

        HerdSireModel = None
        try:
            HerdSireModel = apps.get_model("cattle_tracker_app", "HerdSire")
        except Exception:
            HerdSireModel = None

        LeasedBullModel = None
        try:
            LeasedBullModel = apps.get_model("cattle_tracker_app", "LeasedBull")
        except Exception:
            LeasedBullModel = None

        # Optional pasture field support (if your form exposes it)
        if "pasture" in self.fields:
            self.fields["pasture"].queryset = Pasture.objects.filter(is_active=True).order_by("name")
            self.fields["pasture"].required = False
            self.fields["pasture"].empty_label = "— Select Pasture —"

        # Paddock: filter by allowed owners + active status; label with breadcrumb
        if "paddock" in self.fields:
            qs = Paddock.objects.filter(is_active=True, pasture__is_active=True)
            if self._user is not None:
                owner_ids = get_user_allowed_owners(self._user)
                if owner_ids:
                    qs = qs.filter(pasture__owner_id__in=owner_ids)
            qs = qs.select_related("pasture", "pasture__land_property").order_by(
                "pasture__land_property__name", "pasture__name", "name"
            )
            self.fields["paddock"].queryset = qs
            self.fields["paddock"].required = False  # allow blank if model allows null/blank

            def _label(p):
                lp = getattr(getattr(p.pasture, "land_property", None), "name", None)
                lp_part = f"{lp} → " if lp else ""
                return f"{lp_part}{p.pasture.name} → {p.name}"

            self.fields["paddock"].label_from_instance = _label

        # Herd sire dropdown (if present on the form)
        if "herd_sire" in self.fields:
            if HerdSireModel:
                self.fields["herd_sire"].queryset = HerdSireModel.objects.all().order_by("name")
            else:
                self.fields["herd_sire"].queryset = self.fields["herd_sire"].queryset.none()

        # Natural sire candidates: bulls 16+ months, alive
        if "sire" in self.fields:
            bull_cutoff = date.today() - relativedelta(months=16)
            self.fields["sire"].queryset = CattleModel.objects.filter(
                animal_type="bull", sex="male", dob__lte=bull_cutoff, status="alive"
            ).order_by("ear_tag")

        # Leased bull dropdown (optional—only on edit context per your pattern)
        if "leased_bull" in self.fields:
            if self._context == "edit_cattle" and LeasedBullModel:
                self.fields["leased_bull"].queryset = LeasedBullModel.objects.all().order_by("ear_tag")
                self.fields["leased_bull"].required = False
                self.fields["leased_bull"].empty_label = "— Select Leased Bull —"
            else:
                self.fields["leased_bull"].queryset = self.fields["leased_bull"].queryset.none()

    # ────────────────────────────────────────────────────────────────────────────
    # Validation hooks
    # ────────────────────────────────────────────────────────────────────────────
    def clean(self):
        cleaned = super().clean()
        method = cleaned.get("breeding_method")
        is_leased = cleaned.get("is_leased")
        leased_bull = cleaned.get("leased_bull")

        # If natural + leased flag, leased_bull must be provided
        if method == "natural" and is_leased and not leased_bull:
            self.add_error("leased_bull", ValidationError("Select a leased bull when 'Leased Bull?' is checked."))

        # Access guard: ensure selected paddock belongs to user's allowed owners
        paddock = cleaned.get("paddock")
        if paddock is not None and self._user is not None:
            owner_ids = get_user_allowed_owners(self._user) or []
            if owner_ids and getattr(getattr(paddock, "pasture", None), "owner_id", None) not in owner_ids:
                self.add_error("paddock", ValidationError("You don't have access to this paddock."))

        return cleaned

    def clean_paddock(self):
        value = self.cleaned_data.get("paddock")
        if not value:
            return value
        # Ensure paddock and its pasture are active
        if value and (not getattr(value, "is_active", True) or (hasattr(value, "pasture") and not getattr(value.pasture, "is_active", True))):
            raise ValidationError("Selected paddock is inactive.")
        return value


# Admin form used by the Django admin
class CattleAdminForm(CattleForm):
    """
    In admin, override ModelAdmin.get_form to pass request.user:

        @admin.register(Cattle)
        class CattleAdmin(admin.ModelAdmin):
            form = CattleAdminForm
            def get_form(self, request, obj=None, **kwargs):
                Base = super().get_form(request, obj, **kwargs)
                class RequestAwareForm(Base):
                    def __init__(self, *a, **k):
                        k.setdefault('user', request.user)
                        k.setdefault('context', 'admin')
                        super().__init__(*a, **k)
                return RequestAwareForm
    """
    pass
