# cattle_tracker_app/views/paddock_views.py
from __future__ import annotations

import json
from django.urls import reverse

from decimal import Decimal, InvalidOperation
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponseBadRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.decorators import method_decorator
from django.views.decorators.http import require_POST
from django.views.generic import DetailView

from cattle_tracker_app.models import Paddock

# 🔧 IMPORTANT:
# Adjust this import to match where your PaddockForm actually lives.
try:
    from cattle_tracker_app.forms import PaddockForm
except ImportError:
    # from cattle_tracker_app.forms.paddock_forms import PaddockForm
    PaddockForm = None  # placeholder so the module imports; fail loudly if used


def _normalize_geojson(value):
    """
    Accepts:
      - None
      - str (already JSON)
      - dict / list (Python object)
      - GEOSGeometry-like object with .geojson

    Returns a JSON string or None.
    """
    if value is None:
        return None

    # Already a JSON string?
    if isinstance(value, str):
        return value

    # dict/list → dump to JSON string
    if isinstance(value, (dict, list)):
        return json.dumps(value)

    # Fallback: geometry-like with `.geojson`
    return getattr(value, "geojson", None)


# ============================
# Create view (matches urls.py)
# ============================
@login_required
def paddock_create_view(request):
    """
    Simple create view for Paddock, matching:
      path('paddocks/new/', paddock_create_view, name='paddock_create')
    """

    if PaddockForm is None:
        raise ImportError(
            "PaddockForm could not be imported. "
            "Update the import in paddock_views.py to point to your actual form."
        )

    if request.method == "POST":
        form = PaddockForm(request.POST)
        if form.is_valid():
            paddock = form.save()
            messages.success(request, f"Paddock '{paddock}' created.")
            return redirect("paddock_detail", pk=paddock.pk)
    else:
        initial = {}
        # Optional: pre-select pasture if ?pasture=<id> in query string
        pasture_id = request.GET.get("pasture")
        if pasture_id:
            initial["pasture"] = pasture_id

        form = PaddockForm(initial=initial)

    return render(
        request,
        "pastures/paddock_create.html",  # adjust if your template path differs
        {
            "form": form,
            "page_title": "New Paddock",
        },
    )


# ============================
# Detail view
# ============================
@method_decorator(login_required, name="dispatch")
class PaddockDetailView(DetailView):
    model = Paddock
    template_name = "pastures/paddock_detail.html"
    context_object_name = "paddock"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        paddock = self.object
        pasture = getattr(paddock, "pasture", None)

        ctx["pasture"] = pasture
        ctx["page_title"] = f"Paddock {paddock.name} · {pasture.name if pasture else ''}"

        # If your model uses different field names, tweak these:
        ctx["paddock_acres"] = getattr(paddock, "acres", None)
        ctx["pasture_acres"] = getattr(pasture, "total_acres", None) if pasture else None

        # Robust handling of boundary → JSON string
        boundary = getattr(paddock, "boundary", None)
        pasture_boundary = getattr(pasture, "boundary", None) if pasture else None

        ctx["paddock_geojson"] = _normalize_geojson(boundary)
        ctx["pasture_geojson"] = _normalize_geojson(pasture_boundary)

        # 🔹 Inline-edit endpoint for JS
        ctx["update_url"] = reverse("paddock_update_field", args=[paddock.pk])

        return ctx



# ============================
# Inline field update (AJAX)
# ============================
@login_required
@require_POST
def paddock_update_field(request: HttpRequest, pk: int):
    paddock = get_object_or_404(Paddock, pk=pk)

    # 👇 If you want owner scoping, you can add it here later
    # owner_ids = get_user_allowed_owners(request.user)
    # if paddock.pasture.owner_id not in owner_ids:
    #     return JsonResponse({"ok": False, "error": "Not allowed"}, status=403)

    try:
        payload = json.loads(request.body.decode("utf-8"))
    except json.JSONDecodeError:
        return HttpResponseBadRequest("Invalid JSON")

    field = payload.get("field")
    raw_value = payload.get("value")

    # 🔧 Adjust to match your Paddock model
    ALLOWED_FIELDS = {
        "name": str,
        "acres": Decimal,
        "notes": str,
        # add more fields here if you want them editable
        # "grass_type": str,
    }

    if field not in ALLOWED_FIELDS:
        return JsonResponse(
            {"ok": False, "error": f"Field '{field}' not editable."},
            status=400,
        )

    caster = ALLOWED_FIELDS[field]

    try:
        if caster is Decimal:
            if raw_value in (None, "", "null"):
                value = None
            else:
                value = Decimal(str(raw_value))
        else:
            value = caster(raw_value) if raw_value is not None else ""
    except (InvalidOperation, ValueError, TypeError) as exc:
        return JsonResponse(
            {"ok": False, "error": f"Invalid value for {field}: {exc}"},
            status=400,
        )

    setattr(paddock, field, value)
    paddock.save(update_fields=[field])

    # Format for display
    display_value = getattr(paddock, field)
    if isinstance(display_value, Decimal):
        display_value = f"{display_value.normalize():f}"

    return JsonResponse(
        {
            "ok": True,
            "field": field,
            "value": display_value,
        }
    )



# ============================
# Boundary update (GeoJSON)
# ============================
@login_required
@require_POST
def paddock_update_boundary(request, pk):
    """
    Accepts raw GeoJSON (Feature or FeatureCollection) in the request body
    and saves it into paddock.boundary.

    This assumes paddock.boundary is a JSONField or similar. If you're using
    GEOSGeometry instead, replace the assignment with GEOSGeometry(...) usage.
    """
    paddock = get_object_or_404(Paddock, pk=pk)

    try:
        # If JS sends JSON.stringify(geojson) in the body
        body = request.body.decode("utf-8").strip()
        if not body:
            return HttpResponseBadRequest("Empty body")

        geojson_obj = json.loads(body)
    except json.JSONDecodeError:
        return HttpResponseBadRequest("Invalid JSON")

    # 🔧 If boundary is a JSONField, this is fine:
    paddock.boundary = geojson_obj
    # 🔧 If boundary is a GeometryField, you might instead do:
    # from django.contrib.gis.geos import GEOSGeometry
    # paddock.boundary = GEOSGeometry(json.dumps(geojson_obj), srid=4326)

    paddock.save(update_fields=["boundary"])

    return JsonResponse({"ok": True})
