# cattle_tracker_app/views/api/paddocks_api.py

from __future__ import annotations

import json
from typing import Any, Dict, Optional

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpRequest
from django.views.decorators.http import require_http_methods
from django.contrib.gis.geos import GEOSGeometry, MultiPolygon, Polygon
from cattle_tracker_app.models import Paddock, Pasture  # adjust if modular


def _bad(msg: str, status: int = 400) -> JsonResponse:
    return JsonResponse({"ok": False, "error": msg}, status=status)


def _parse_json_body(request: HttpRequest) -> Optional[Dict[str, Any]]:
    try:
        raw = request.body.decode("utf-8") if request.body else ""
        return json.loads(raw or "{}")
    except Exception:
        return None


def _normalize_geom(val: Any) -> Optional[Dict[str, Any]]:
    """
    Accept dict GeoJSON geometry, or a JSON string containing it.
    Return None if invalid.
    """
    if not val:
        return None
    if isinstance(val, dict):
        return val
    if isinstance(val, str):
        try:
            parsed = json.loads(val)
            return parsed if isinstance(parsed, dict) else None
        except Exception:
            return None
    return None


def _geom_is_valid(geom: Dict[str, Any]) -> bool:
    return (
        isinstance(geom, dict)
        and isinstance(geom.get("type"), str)
        and "coordinates" in geom
    )


def _as_feature(paddock: Paddock, geom: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "type": "Feature",
        "id": paddock.id,
        "geometry": geom,
        "properties": {
            "id": paddock.id,
            "name": getattr(paddock, "name", "") or "",
            "pasture_id": paddock.pasture_id,
            "detail_url": f"/pastures/paddock/{paddock.id}/",
            "layer_type": "paddock",
        },
    }


@login_required
@require_http_methods(["GET", "POST", "OPTIONS"])
def api_paddocks_view(request: HttpRequest) -> JsonResponse:
    """
    GET  /api/paddocks/                -> GeoJSON FeatureCollection of all paddocks
    GET  /api/paddocks/?pasture=<id>   -> paddocks filtered to a pasture
    POST /api/paddocks/                -> create paddock from GeoJSON geometry (for map drawing)

    POST body JSON (recommended):
      {
        "pasture_id": 1,
        "name": "Paddock 3",
        "geometry": {"type":"Polygon","coordinates":[...]}
      }

    Also accepts:
      - "pasture" as alias for pasture_id
      - "boundary" as alias for geometry
    """
    if request.method == "GET":
        qs = Paddock.objects.select_related("pasture").all().order_by("id")

        pasture_filter = request.GET.get("pasture")
        if pasture_filter:
            qs = qs.filter(pasture_id=pasture_filter)

        features: list[Dict[str, Any]] = []

        for pd in qs:
            # <-- CHANGE THIS if your model field isn't named "boundary"
            geom_val = getattr(pd, "boundary", None)
            geom = _normalize_geom(geom_val)

            if not geom or not _geom_is_valid(geom):
                # Skip paddocks missing/invalid geometry
                continue

            features.append(_as_feature(pd, geom))

        return JsonResponse({"type": "FeatureCollection", "features": features})

    # -------------------------
    # POST: create paddock
    # -------------------------
    data = _parse_json_body(request)
    if data is None:
        return _bad("Invalid JSON body")

    pasture_id = data.get("pasture_id") or data.get("pasture")
    name = (data.get("name") or "").strip() or "New Paddock"

    # Accept geometry in either `geometry` or `boundary`
    #geom = _normalize_geom(data.get("geometry") or data.get("boundary"))
    geom = _to_geos_multipolygon(geom_in)

    if not pasture_id:
        return _bad("Missing pasture_id (or pasture)")
    if not geom or not _geom_is_valid(geom):
        return _bad("Missing/invalid geometry (GeoJSON geometry required)")

    if geom.get("type") not in ("Polygon", "MultiPolygon"):
        return _bad("Geometry must be Polygon or MultiPolygon")

    if not Pasture.objects.filter(id=pasture_id).exists():
        return _bad("Pasture not found", status=404)

    # Create paddock
    pd = Paddock(
        pasture_id=pasture_id,
        name=name,
    )
    # <-- CHANGE THIS if your model field isn't named "boundary"
    setattr(pd, "boundary", geom)
    pd.save()

    return JsonResponse(_as_feature(pd, geom), status=201)
    
    def _to_geos_multipolygon(geom):
    if geom is None:
        raise TypeError("Missing geometry")

    if isinstance(geom, dict):
        g = GEOSGeometry(json.dumps(geom), srid=4326)
    elif isinstance(geom, str):
        g = GEOSGeometry(geom, srid=4326)
    else:
        raise TypeError(f"Unsupported geometry type: {type(geom)}")

    # Wrap Polygon → MultiPolygon
    if isinstance(g, Polygon):
        return MultiPolygon(g)

    if isinstance(g, MultiPolygon):
        return g

    raise TypeError(f"Geometry must be Polygon or MultiPolygon, got: {g.geom_type}")