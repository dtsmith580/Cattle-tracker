from __future__ import annotations

# =============================
# cattle_views.py — full drop-in (patched)
# =============================
# Includes:
# - Owner scoping helper (get_user_allowed_owners / _apply_owner_scope)
# - Enhanced filters (Owner, Animal Type, Status, Pasture) + sortable table order
# - cattle_list + legacy alias cattle_list_view
# - CattleDetailView (CBV)
# - add_cattle_view (FBV)
# - update_cattle_field (AJAX)
# - CattleCreateView / CattleUpdateView (CBVs)
# - edit_cattle_view (FBV wrapper)
# - delete_cattle_view + alias delete_cattle
# - export_cattle_csv
# - mark_cattle_sold / mark_cattle_dead / bulk_mark_cattle_sold
# - add_weight_log (basic)
# - cattle_card_partial (partial renderer)
# - __all__ exports to match urls.py imports

from typing import List
from decimal import Decimal, InvalidOperation
from datetime import date
import csv
import json

from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.db.models import OuterRef, Subquery, F

from django.http import (
    HttpRequest,
    HttpResponse,
    JsonResponse,
    HttpResponseBadRequest,
)
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse
from django.utils.timezone import now
from django.views.decorators.http import require_POST
from django.views.generic import DetailView, CreateView, UpdateView

from cattle_tracker_app.models import Cattle, Owner, Pasture, Paddock

# -----------------------------------------------------------------------------
# Owner scoping helper
# -----------------------------------------------------------------------------
try:
    from cattle_tracker_app.utils.access import get_user_allowed_owners  # type: ignore
except Exception:
    try:
        from cattle_tracker_app.models.ownership_models import OwnerUserAccess  # type: ignore
    except Exception:
        OwnerUserAccess = None  # type: ignore

    def get_user_allowed_owners(user) -> List[int]:
        if not getattr(user, "is_authenticated", False):
            return []
        if user.is_superuser or user.groups.filter(name__in=["Admin", "Dev"]).exists():
            return []  # unrestricted
        if OwnerUserAccess is None:
            return []
        return list(
            OwnerUserAccess.objects.filter(user=user).values_list("owner_id", flat=True)
        )

GLOBAL_GROUPS = ["Admin", "Dev"]
DEFAULT_PAGE_SIZE = 25


def _apply_owner_scope(qs, request: HttpRequest):
    """Scope queryset to user's owners; returns (scoped_qs, owner_scope_ids).
    Empty owner_scope_ids means unrestricted (Admins/Devs/superuser)."""
    user = request.user
    if user.is_superuser or user.groups.filter(name__in=GLOBAL_GROUPS).exists():
        return qs, []
    owner_ids = get_user_allowed_owners(user)
    if owner_ids:
        return qs.filter(owner_id__in=owner_ids), owner_ids
    return qs, owner_ids


# -----------------------------------------------------------------------------
# Filter helpers (Owner, Animal Type, Status, Pasture) and enhanced filtering
# -----------------------------------------------------------------------------

def _get_filter_options(request: HttpRequest):
    """Build dropdown options for Owner, Animal Type, Status, and Pasture (owner-scoped)."""
    qs_scoped, owner_scope_ids = _apply_owner_scope(Cattle.objects.all(), request)

    owners_qs = Owner.objects.all()
    if owner_scope_ids:
        owners_qs = owners_qs.filter(id__in=owner_scope_ids)
    owners_qs = owners_qs.order_by("name")

    animal_types = (
        qs_scoped.exclude(animal_type__isnull=True)
        .exclude(animal_type="")
        .values_list("animal_type", flat=True)
        .distinct()
        .order_by("animal_type")
    )

    try:
        status_field = Cattle._meta.get_field("status")
        statuses = [c[0] for c in getattr(status_field, "choices", [])] or list(
            qs_scoped.values_list("status", flat=True).distinct().order_by("status")
        )
    except Exception:
        statuses = ["Alive", "Sold", "Dead"]

    pastures_qs = Pasture.objects.all().order_by("name")

    return {
        "owners": owners_qs,
        "animal_types": list(animal_types),
        "statuses": list(statuses),
        "pastures": pastures_qs,
    }


def _apply_filters_enhanced(qs, request: HttpRequest):
    """Apply filters incl. explicit status/pasture + sortable order with '-' support."""
    params = request.GET

    # --- STATUS: explicit OR default to Alive ---
    status_raw = params.get("status", "").strip()
    if status_raw:
        wanted_status = [x.strip() for x in status_raw.split(",") if x.strip()]
        if wanted_status:
            qs = qs.filter(status__in=wanted_status)
    else:
        # Default: only Alive
        qs = qs.filter(status__iexact="Alive")

    # Animal type
    animal_types_raw = params.get("animal_type", "").strip()
    if animal_types_raw:
        wanted = [x.strip() for x in animal_types_raw.split(",") if x.strip()]
        if wanted:
            qs = qs.filter(animal_type__in=wanted)

    # Sex (legacy)
    sex = params.get("sex", "").strip()
    if sex:
        qs = qs.filter(sex__iexact=sex)

    # Owner (comma-separated ids)
    owner_raw = params.get("owner", "").strip()
    if owner_raw:
        try:
            owner_ids_filter = [int(x) for x in owner_raw.split(",") if x]
            if owner_ids_filter:
                qs = qs.filter(owner_id__in=owner_ids_filter)
        except ValueError:
            pass

    # Pasture (single id)
    pasture_id = params.get("pasture", "").strip()
    if pasture_id.isdigit():
        qs = qs.filter(pasture_id=int(pasture_id))

    # DOB range
    dob_start = params.get("dob_start", "").strip()
    dob_end = params.get("dob_end", "").strip()
    if dob_start:
        qs = qs.filter(dob__gte=dob_start)
    if dob_end:
        qs = qs.filter(dob__lte=dob_end)

    # Text search
    q = params.get("q", "").strip()
    if q:
        qs = qs.filter(
            Q(ear_tag__icontains=q)
            | Q(registration_number__icontains=q)
            | Q(owner__name__icontains=q)
        )

    # Ordering (+support '-' prefix)
    order = params.get("order", "ear_tag").strip()
    allowed = {
        "ear_tag", "-ear_tag",
        "dob", "-dob",
        "animal_type", "-animal_type",
        "status", "-status",
        "owner__name", "-owner__name",
        "pasture__name", "-pasture__name",
        "paddock__name", "-paddock__name",
        "date_added", "-date_added",
    }
    if order in allowed:
        qs = qs.order_by(order)
    else:
        qs = qs.order_by("ear_tag")

    return qs

def _annotate_latest_weight_if_missing(qs):
    """
    If the Cattle model doesn't have a real latest_weight field,
    annotate one from the newest WeightLog. Otherwise, return qs unchanged.
    """
    try:
        Cattle._meta.get_field("latest_weight")  # real field exists
        return qs
    except Exception:
        pass

    # Only annotate if WeightLog is available
    try:
        from cattle_tracker_app.models import WeightLog  # local import to avoid top-level issues
    except Exception:
        return qs

    latest_weight_sq = (
        WeightLog.objects
        .filter(cattle_id=OuterRef("pk"))
        .order_by("-date", "-id")
        .values("weight")[:1]
    )
    return qs.annotate(latest_weight=Subquery(latest_weight_sq))







# -----------------------------------------------------------------------------
# List & Detail Views
# -----------------------------------------------------------------------------

@login_required
def cattle_list(request: HttpRequest) -> HttpResponse:
    qs = (
    Cattle.objects.select_related(
        "owner", "pasture", "paddock", "sire", "dam", "herd_sire"
    ).all()
    )

    # Ensure latest_weight is present for the table (annotation if needed)
    qs = _annotate_latest_weight_if_missing(qs)

    qs, owner_scope_ids = _apply_owner_scope(qs, request)
    qs = _apply_filters_enhanced(qs, request)

    # Alive count now strictly equals status=Alive
    alive_count = Cattle.objects.filter(status__iexact="Alive").count()

    try:
        page_size = int(request.GET.get("page_size", DEFAULT_PAGE_SIZE))
    except ValueError:
        page_size = DEFAULT_PAGE_SIZE
    page_size = max(1, min(250, page_size))

    paginator = Paginator(qs, page_size)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    context = {
        "page_obj": page_obj,
        "total_count": paginator.count,
        "alive_count": alive_count,
        "q": request.GET.get("q", "").strip(),
        "order": request.GET.get("order", "ear_tag"),
        "page_size": page_size,
        "owner_scope_ids": owner_scope_ids,
    }

    opts = _get_filter_options(request)
    context.update({
        "owner_options": opts.get("owners"),
        "animal_type_options": opts.get("animal_types"),
        "status_options": opts.get("statuses"),
        "pasture_options": opts.get("pastures"),
        "selected_owner": request.GET.get("owner", ""),
        "selected_animal_type": request.GET.get("animal_type", ""),
        # Default the dropdown selection to Alive for first load
        "selected_status": request.GET.get("status", "Alive"),
        "selected_pasture": request.GET.get("pasture", ""),
    })

    return render(request, "cattle/cattle_list.html", context)


# Back-compat alias for legacy import paths
@login_required
def cattle_list_view(request: HttpRequest) -> HttpResponse:
    return cattle_list(request)


class CattleDetailView(DetailView):
    model = Cattle
    template_name = "cattle/view_cattle.html"
    context_object_name = "cattle"
    pk_url_kwarg = "pk"


# -----------------------------------------------------------------------------
# Create / Update / Inline Update / Delete
# -----------------------------------------------------------------------------

@login_required
def add_cattle_view(request: HttpRequest) -> HttpResponse:
    """Create a new Cattle record with owner-scoped choices."""
    try:
        from cattle_tracker_app.forms import CattleForm  # type: ignore
    except Exception:
        from django.forms import ModelForm
        class CattleForm(ModelForm):
            class Meta:
                model = Cattle
                fields = [
                    "ear_tag", "animal_type", "sex", "dob", "owner",
                    "pasture", "paddock", "status", "registration_number",
                    "herd_sire", "sire", "dam", "date_added",
                ]

    if request.method == "POST":
        form = CattleForm(request.POST, request.FILES)
    else:
        form = CattleForm()

    owner_ids = get_user_allowed_owners(request.user)
    if owner_ids and "owner" in form.fields:
        form.fields["owner"].queryset = Owner.objects.filter(id__in=owner_ids)

    if request.method == "POST" and form.is_valid():
        cow = form.save()
        return redirect(reverse("view_cattle", kwargs={"pk": cow.pk}))

    return render(request, "cattle/cattle_form.html", {"form": form})


@login_required
def cattle_card_partial(request: HttpRequest, pk: int) -> HttpResponse:
    """
    Partial renderer for the cattle profile card.
    Provides owners and pasture_options so dropdowns populate in edit mode.
    """
    cow = get_object_or_404(
        Cattle.objects.select_related("owner", "pasture", "paddock"),
        pk=pk
    )

    # Force-evaluate lists to avoid lazy eval gotchas and ensure template has data
    owners_list = list(Owner.objects.order_by("name"))
    pastures_list = list(Pasture.objects.order_by("name"))

    context = {
        "cattle": cow,
        "owners": owners_list,
        # both keys for compatibility with any template variants
        "owner_options": owners_list,
        "pasture_options": pastures_list,
        "pastures": pastures_list,
    }
    return render(request, "cattle/_profile_card.html", context)


@login_required
@permission_required("cattle_tracker_app.change_cattle", raise_exception=True)
@require_POST
def update_cattle_field(request, pk):
    """
    Unified inline updater:
      • Regular field update: form-encoded {<fieldName>=<value>} OR JSON {"field","value"}
      • Image upload: multipart with 'image' file
      • Delete image: form-encoded {delete_image=1}
    Returns: {"status":"success", "field": <field>, "value": <raw>, "display": <pretty>}
    """
    from django.utils.dateparse import parse_date

    cow = get_object_or_404(Cattle, pk=pk)

    # --- Image delete ---
    if request.POST.get("delete_image"):
        if getattr(cow, "image", None):
            try:
                cow.image.delete(save=False)
            except Exception:
                pass
            cow.image = None
            cow.save(update_fields=["image"])
        return JsonResponse({"status": "success", "field": "image", "value": None, "display": "—"})

    # --- Image upload ---
    if "image" in request.FILES:
        cow.image = request.FILES["image"]
        cow.save(update_fields=["image"])
        url = cow.image.url if cow.image else None
        return JsonResponse({"status": "success", "field": "image", "value": url, "display": url or "—"})

    # Try JSON first, then fallback to single form field (name=value)
    payload = None
    if request.META.get("CONTENT_TYPE", "").startswith("application/json"):
        try:
            payload = json.loads(request.body.decode("utf-8") or "{}")
        except json.JSONDecodeError:
            return HttpResponseBadRequest("Invalid JSON")

    if payload:
        field = (payload.get("field") or "").strip()
        raw_value = (payload.get("value") or "")
    else:
        # Extract the single non-CSRF posted field
        editable_items = [(k, v) for k, v in request.POST.items()
                          if k not in ("csrfmiddlewaretoken", "X-Requested-With")]
        if not editable_items:
            return HttpResponseBadRequest("Missing field")
        if len(editable_items) > 1:
            return HttpResponseBadRequest("Too many fields")
        field, raw_value = editable_items[0]
        field = (field or "").strip()

    # Whitelist allowed fields (align with your UI)
    ALLOWED = {
        # simple strings / choices
        "ear_tag": "str",
        "status": "str",
        "animal_type": "str",
        "sex": "str",
        "registration_number": "str",
        "notes": "str",

        # numbers / dates
        "latest_weight": "decimal",
        "dob": "date",

        # foreign keys
        "owner": "fk_owner",
        "pasture": "fk_pasture",
        "paddock": "fk_paddock",

        # legacy booleans (if you still use them in UI)
        "is_sold": "bool",
        "is_dead": "bool",
    }
    ftype = ALLOWED.get(field)
    if not ftype:
        return HttpResponseBadRequest("Field not allowed")

    raw_value = "" if raw_value is None else str(raw_value).strip()

    # Coerce & set
    try:
        if ftype == "str":
            setattr(cow, field, raw_value)

        elif ftype == "date":
            if raw_value == "":
                setattr(cow, field, None)
            else:
                d = parse_date(raw_value)  # expects YYYY-MM-DD
                if not d:
                    return HttpResponseBadRequest("Invalid date")
                setattr(cow, field, d)

        elif ftype == "decimal":
            if raw_value == "":
                setattr(cow, field, None)
            else:
                try:
                    setattr(cow, field, Decimal(raw_value))
                except (InvalidOperation, ValueError):
                    return HttpResponseBadRequest("Invalid number")

        elif ftype == "bool":
            setattr(cow, field, raw_value.lower() in {"1", "true", "yes", "on"})

        elif ftype == "fk_owner":
            if raw_value == "":
                cow.owner = None
            else:
                try:
                    cow.owner = Owner.objects.get(pk=int(raw_value))
                except (Owner.DoesNotExist, ValueError, TypeError):
                    return HttpResponseBadRequest("Invalid owner")

        elif ftype == "fk_pasture":
            if raw_value == "":
                cow.pasture = None
            else:
                try:
                    cow.pasture = Pasture.objects.get(pk=int(raw_value))
                except (Pasture.DoesNotExist, ValueError, TypeError):
                    return HttpResponseBadRequest("Invalid pasture")

        elif ftype == "fk_paddock":
            if raw_value == "":
                cow.paddock = None
            else:
                try:
                    cow.paddock = Paddock.objects.get(pk=int(raw_value))
                except (Paddock.DoesNotExist, ValueError, TypeError):
                    return HttpResponseBadRequest("Invalid paddock")
        else:
            return HttpResponseBadRequest("Unsupported type")

    except Exception:
        return HttpResponseBadRequest("Bad value")

    # Validate & save
    try:
        cow.full_clean()
        cow.save()
    except Exception:
        return HttpResponseBadRequest("Validation error")

    # Pretty display back to UI
    def display_for(fld):
        v = getattr(cow, fld)
        if fld in ("owner", "pasture", "paddock"):
            return v.name if v else "—"
        if fld == "dob":
            return v.isoformat() if v else "—"
        if fld == "latest_weight":
            return f"{v} lbs" if v is not None else "—"
        return v if (v not in [None, ""]) else "—"

    return JsonResponse({
        "status": "success",
        "id": cow.pk,
        "field": field,
        "value": getattr(cow, field),
        "display": display_for(field),
    })


class CattleCreateView(CreateView):
    model = Cattle
    template_name = "cattle/cattle_form.html"

    try:
        from cattle_tracker_app.forms import CattleForm  # type: ignore
        form_class = CattleForm
    except Exception:
        from django.forms import ModelForm
        class _FallbackForm(ModelForm):
            class Meta:
                model = Cattle
                fields = [
                    "ear_tag", "animal_type", "sex", "dob", "owner",
                    "pasture", "paddock", "status", "registration_number",
                    "herd_sire", "sire", "dam", "date_added",
                ]
        form_class = _FallbackForm

    def get_success_url(self):
        return reverse("view_cattle", kwargs={"pk": self.object.pk})

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        owner_ids = get_user_allowed_owners(self.request.user)
        if owner_ids and "owner" in form.fields:
            form.fields["owner"].queryset = Owner.objects.filter(id__in=owner_ids)
        return form


class CattleUpdateView(UpdateView):
    model = Cattle
    template_name = "cattle/cattle_form.html"
    context_object_name = "cattle"

    try:
        from cattle_tracker_app.forms import CattleForm  # type: ignore
        form_class = CattleForm
    except Exception:
        from django.forms import ModelForm
        class _FallbackForm(ModelForm):
            class Meta:
                model = Cattle
                fields = [
                    "ear_tag", "animal_type", "sex", "dob", "owner",
                    "pasture", "paddock", "status", "registration_number",
                    "herd_sire", "sire", "dam", "date_added",
                ]
        form_class = _FallbackForm

    def get_success_url(self):
        return reverse("view_cattle", kwargs={"pk": self.object.pk})

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        owner_ids = get_user_allowed_owners(self.request.user)
        if owner_ids and "owner" in form.fields:
            form.fields["owner"].queryset = Owner.objects.filter(id__in=owner_ids)
        return form


@login_required
def edit_cattle_view(request: HttpRequest, pk: int) -> HttpResponse:
    """Back-compat wrapper around CattleUpdateView."""
    view = CattleUpdateView.as_view()
    return view(request, pk=pk)


@login_required
def delete_cattle_view(request: HttpRequest, pk: int) -> HttpResponse:
    cow = get_object_or_404(Cattle, pk=pk)
    if request.method == "POST":
        cow.delete()
        messages.success(request, "Cattle deleted.")
        return redirect(reverse("cattle_list"))
    return render(request, "cattle/confirm_delete.html", {"cattle": cow})

# Back-compat alias
delete_cattle = delete_cattle_view


# -----------------------------------------------------------------------------
# Export / Status Updates / Weight Log
# -----------------------------------------------------------------------------

@login_required
def export_cattle_csv(request: HttpRequest) -> HttpResponse:
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = f"attachment; filename=cattle_{now().date()}.csv"
    writer = csv.writer(response)
    writer.writerow(["ID", "Ear Tag", "Status", "Owner", "Animal Type", "DOB"])
    qs = Cattle.objects.all()
    qs, _owner_scope = _apply_owner_scope(qs, request)
    for c in qs.order_by("ear_tag"):
        writer.writerow([c.id, c.ear_tag, c.status, getattr(c.owner, "name", ""), c.animal_type, c.dob])
    return response


@login_required
def mark_cattle_sold(request: HttpRequest, pk: int) -> HttpResponse:
    cow = get_object_or_404(Cattle, pk=pk)
    cow.status = "sold"
    cow.save(update_fields=["status"])
    messages.success(request, f"Marked {cow.ear_tag} as sold.")
    return redirect(reverse("view_cattle", kwargs={"pk": pk}))


@login_required
def mark_cattle_dead(request: HttpRequest, pk: int) -> HttpResponse:
    cow = get_object_or_404(Cattle, pk=pk)
    cow.status = "dead"
    cow.save(update_fields=["status"])
    messages.success(request, f"Marked {cow.ear_tag} as dead.")
    return redirect(reverse("view_cattle", kwargs={"pk": pk}))


@login_required
def bulk_mark_cattle_sold(request: HttpRequest) -> HttpResponse:
    ids = request.POST.get("ids", "").strip()
    id_list = [int(x) for x in ids.split(",") if x.strip().isdigit()]
    if id_list:
        Cattle.objects.filter(pk__in=id_list).update(status="sold")
        messages.success(request, f"Marked {len(id_list)} cattle as sold.")
    else:
        messages.warning(request, "No valid IDs provided.")
    return redirect(reverse("cattle_list"))


try:
    from cattle_tracker_app.models import WeightLog  # type: ignore
except Exception:
    WeightLog = None  # type: ignore


@login_required
def add_weight_log(request: HttpRequest, pk: int) -> HttpResponse:
    cow = get_object_or_404(Cattle, pk=pk)
    if WeightLog is None:
        return JsonResponse({"error": "WeightLog model not available"}, status=400)
    if request.method == "POST":
        try:
            weight = request.POST.get("weight")
            date_str = request.POST.get("date")
            WeightLog.objects.create(
                cattle=cow,
                weight=float(weight) if weight else None,
                date=date.fromisoformat(date_str) if date_str else now().date(),
            )
            messages.success(request, "Weight log added.")
            return redirect(reverse("view_cattle", kwargs={"pk": pk}))
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)
    return render(request, "cattle/add_weight_log.html", {"cattle": cow})


# Explicit re-exports for package-level imports
__all__ = [
    "CattleDetailView",
    "cattle_list",
    "cattle_list_view",
    "add_cattle_view",
    "update_cattle_field",
    "CattleCreateView",
    "CattleUpdateView",
    "edit_cattle_view",
    "delete_cattle_view",
    "delete_cattle",
    "export_cattle_csv",
    "mark_cattle_sold",
    "mark_cattle_dead",
    "bulk_mark_cattle_sold",
    "add_weight_log",
    "cattle_card_partial",
]
