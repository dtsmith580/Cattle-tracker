# cattle_tracker_app/views/pasture_views.py
from __future__ import annotations

import json
from decimal import Decimal, InvalidOperation
from typing import Any, Optional

from django.contrib.auth.decorators import login_required, permission_required
from django.http import JsonResponse, HttpResponseBadRequest, HttpResponse
from django.shortcuts import get_object_or_404, render, redirect
from django.utils.decorators import method_decorator
from django.views.decorators.http import require_POST
from django.views.generic import DetailView
from django.core.exceptions import ValidationError
from cattle_tracker_app.forms import PastureForm  # make sure this import path matches your project
from cattle_tracker_app.models.pasture_models import Pasture

# --- GeoDjango imports (hard requirement since Pasture.geometry is a MultiPolygonField)
from django.contrib.gis.geos import GEOSGeometry, MultiPolygon, GEOSException


# =====================================================================================
# Detail / list / create pages
# =====================================================================================
@method_decorator(login_required, name="dispatch")
class PastureDetailView(DetailView):
    model = Pasture
    template_name = "pastures/pasture_detail.html"


@login_required
def pasture_list_page(request):
    #"""Renders the map/list page at templates/pastures/pasture_list.html"""
    return render(request, 'pastures/pasture_list.html')


@login_required
@permission_required("cattle_tracker_app.add_pasture", raise_exception=True)
def pasture_create_view(request):
    """
    Create a new Pasture with a nice card layout + editable map (boundary).
    Uses templates/pastures/pasture_create.html and PastureForm.
    """
    if request.method == "POST":
        form = PastureForm(request.POST)
        if form.is_valid():
            pasture = form.save()
            messages.success(request, "Pasture created successfully.")
            # redirect to detail or list, whichever you use
            return redirect("pasture_detail", pk=pasture.pk)
        # if form is NOT valid, fall through and re-render the template with errors

    else:
        form = PastureForm()

    # 🔥 IMPORTANT: always return an HttpResponse here for both GET and invalid POST
    return render(request, "pastures/pasture_create.html", {"form": form})


# =====================================================================================
# Helpers
# =====================================================================================

def _safe_json_body(request) -> dict:
    """
    Safely decode JSON once. Supports:
      - application/json
      - application/geo+json
      - any body that 'looks like' a JSON object (starts/ends with braces)
    """
    try:
        ctype = (request.META.get("CONTENT_TYPE") or "").split(";")[0].strip().lower()
    except Exception:
        ctype = ""

    try:
        raw = request.body.decode("utf-8") if request.body else ""
    except Exception:
        raw = ""

    if ctype in {"application/json", "application/geo+json", "text/json"}:
        try:
            return json.loads(raw or "{}")
        except Exception:
            return {}

    # Fallback: if it looks like JSON, try to parse anyway
    if raw and raw.strip().startswith("{") and raw.strip().endswith("}"):
        try:
            return json.loads(raw)
        except Exception:
            return {}

    return {}


def _first_present(d: dict, keys: list[str]) -> Any:
    for k in keys:
        if k in d and d[k] is not None:
            return d[k]
    return None


def _clean_coords_recursive(coords):
    """Drop any null/NaN coord pairs and empty rings/polygons."""
    if not isinstance(coords, list):
        return []
    out = []
    for item in coords:
        if isinstance(item, list):
            cleaned = _clean_coords_recursive(item)
            if cleaned:
                out.append(cleaned)
    # Ring: list of [lng,lat]
    if out and all(isinstance(pt, list) and len(pt) == 2 and pt[0] is not None and pt[1] is not None for pt in out):
        return out if len(out) >= 3 else []
    # Otherwise keep non-empty children
    return [c for c in out if c]


def _normalize_geometry_like(value: Any) -> Optional[dict]:
    """
    Accepts:
      - bare GeoJSON Geometry {type, coordinates}
      - GeoJSON Feature {type:'Feature', geometry:{...}}
      - GeoJSON FeatureCollection -> first feature's geometry
      - stringified versions of the above
    Returns cleaned geometry dict or None.
    """
    if value is None:
        return None

    # If string, try to JSON parse
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except Exception:
            return None

    if not isinstance(value, dict) or "type" not in value:
        return None

    t = value.get("type")
    if t == "Feature":
        geom = value.get("geometry")
        return _normalize_geometry_like(geom)
    if t == "FeatureCollection":
        feats = value.get("features") or []
        if feats and isinstance(feats, list):
            first = feats[0] if feats else None
            if isinstance(first, dict):
                return _normalize_geometry_like(first.get("geometry"))
        return None

    # Must be Polygon or MultiPolygon
    if t not in {"Polygon", "MultiPolygon"}:
        return None
    coords = _clean_coords_recursive(value.get("coordinates"))
    if not coords:
        return None
    return {"type": t, "coordinates": coords}


# =====================================================================================
# Inline field update (strict geometry handling)
# =====================================================================================
@login_required
@require_POST
def pasture_update_field(request: HttpRequest, pk: int) -> HttpResponse:
    """
    Generic inline-update endpoint for Pasture fields.

    Used by:
      - pasture_detail autosave (name, acres)
      - maploader.js saveEdits() for geometry

    Expects POST form data:
      field = <field_name>
      value = <value or GeoJSON string for geometry>
    """
    pasture = get_object_or_404(Pasture, pk=pk)

    field = request.POST.get("field", "").strip()
    raw_value = request.POST.get("value", "").strip()

    if not field:
        return HttpResponseBadRequest("Missing field")

    # ----- name -----
    if field == "name":
        pasture.name = raw_value or None
        pasture.save(update_fields=["name"])

    # ----- acres (Decimal / nullable) -----
    elif field == "acres":
        if raw_value == "":
            pasture.acres = None
        else:
            try:
                pasture.acres = Decimal(raw_value)
            except InvalidOperation:
                return HttpResponseBadRequest("Invalid acres value")
        pasture.save(update_fields=["acres"])

    # ----- geometry (GeoJSON from maploader.js) -----
    elif field == "geometry":
        if raw_value == "":
            # Allow clearing geometry if you want; or reject if not desired
            pasture.geometry = None
            pasture.save(update_fields=["geometry"])
        else:
            # raw_value is a JSON string, e.g. {"type":"Polygon","coordinates":[...]}
            try:
                payload = json.loads(raw_value)
            except json.JSONDecodeError:
                return HttpResponseBadRequest("Invalid geometry payload")

            # Accept either:
            #   - direct geometry {type: Polygon|MultiPolygon, coordinates: ...}
            #   - Feature {type: 'Feature', geometry: {...}}
            #   - FeatureCollection (first feature)
            geom_obj = None

            if isinstance(payload, dict) and "type" in payload:
                t = payload["type"]
                if t in ("Polygon", "MultiPolygon"):
                    geom_obj = payload
                elif t == "Feature" and isinstance(payload.get("geometry"), dict):
                    geom_obj = payload["geometry"]
                elif t == "FeatureCollection":
                    features = payload.get("features") or []
                    if features and isinstance(features[0], dict):
                        geom_obj = features[0].get("geometry")
            if not geom_obj or "type" not in geom_obj or "coordinates" not in geom_obj:
                return HttpResponseBadRequest("Invalid geometry payload")

            try:
                # Convert the dict back to a GeoJSON string for GEOSGeometry
                geojson_str = json.dumps(geom_obj)
                # srid=4326 for lon/lat WGS84
                pasture.geometry = GEOSGeometry(geojson_str, srid=4326)
            except (ValueError, GEOSException):
                return HttpResponseBadRequest("Invalid geometry payload")

            pasture.save(update_fields=["geometry"])

    else:
        # Unknown/unsupported field
        return HttpResponseBadRequest("Unknown field")

    # AJAX-friendly JSON response
    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        return JsonResponse({"ok": True})

    # Fallback: redirect if not AJAX (rare)
    return redirect("pasture_detail", pk=pasture.pk)


# =====================================================================================
# GeoJSON endpoints (server-side guards — return only valid Polygon/MultiPolygon)
# =====================================================================================
@login_required
def pastures_geojson(request):
    feats: list[dict] = []
    for p in Pasture.objects.filter(geometry__isnull=False):
        g = p.geometry
        if not g or g.empty:
            continue
        if g.geom_type not in ("Polygon", "MultiPolygon"):
            continue
        try:
            if hasattr(g, "valid") and not g.valid:
                if hasattr(g, "make_valid"):
                    g = g.make_valid()
                else:
                    continue
            feats.append({
                "type": "Feature",
                "id": p.pk,
                "properties": {
                    "id": p.pk,
                    "name": p.name,
                    "acres": float(p.acres) if p.acres is not None else None,
                },
                "geometry": json.loads(g.geojson),
            })
        except Exception:
            continue
    return JsonResponse({"type": "FeatureCollection", "features": feats})


@login_required
def pasture_geojson(request, pk: int):
    p = get_object_or_404(Pasture, pk=pk)
    g = p.geometry
    if not g or g.empty:
        return HttpResponseBadRequest('Pasture has no geometry')
    if g.geom_type not in ("Polygon", "MultiPolygon"):
        return HttpResponseBadRequest('Pasture geometry must be Polygon or MultiPolygon')
    try:
        if hasattr(g, "valid") and not g.valid:
            if hasattr(g, "make_valid"):
                g = g.make_valid()
            else:
                return HttpResponseBadRequest('Invalid geometry (cannot repair)')
        feature = {
            'type': 'Feature',
            'id': p.id,
            'properties': {
                'id': p.id,
                'name': p.name,
                'acres': float(p.acres) if p.acres is not None else None,
            },
            'geometry': json.loads(g.geojson),
        }
        return JsonResponse(feature)
    except Exception as e:
        return HttpResponseBadRequest(f'Failed to serialize geometry: {e}')
