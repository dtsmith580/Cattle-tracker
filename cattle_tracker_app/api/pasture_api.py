"""
DRF + DRF-GIS GeoJSON API for Pastures & Paddocks
File: cattle_tracker_app/api/pasture_api.py

Notes (based on your logs):
- Your Paddock geometry field is a MultiPolygonField, so we MUST coerce Polygon -> MultiPolygon.
- Leaflet.Draw typically produces Polygon, so POST /api/paddocks/ must wrap it.
- Your existing GET /api/paddocks/ already returns a FeatureCollection; this keeps that working via DRF-GIS.
"""

from __future__ import annotations

import json

from django.contrib.gis.geos import GEOSGeometry, MultiPolygon, Polygon
from rest_framework import serializers, status, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework_gis.serializers import GeoFeatureModelSerializer

from cattle_tracker_app.models import Pasture, Paddock


# -----------------------------
# Geometry helpers
# -----------------------------
def _to_geos_multipolygon(geom) -> MultiPolygon:
    """
    Accepts:
      - GeoJSON dict: {"type": "...", "coordinates": ...}
      - GeoJSON string
      - WKT string (optional)

    Returns: GEOS MultiPolygon with SRID 4326 (lon/lat),
    because your Paddock field is MULTIPOLYGON.
    """
    if geom is None:
        raise TypeError("Missing geometry")

    if isinstance(geom, dict):
        g = GEOSGeometry(json.dumps(geom), srid=4326)
    elif isinstance(geom, str):
        g = GEOSGeometry(geom, srid=4326)
    else:
        raise TypeError(f"Unsupported geometry type: {type(geom)}")

    # Wrap Polygon -> MultiPolygon
    if isinstance(g, Polygon):
        return MultiPolygon(g)

    if isinstance(g, MultiPolygon):
        return g

    raise TypeError(f"Geometry must be Polygon or MultiPolygon, got: {g.geom_type}")


# Backwards-compatible alias (in case any code still calls _to_geos)
_to_geos = _to_geos_multipolygon


# -----------------------------
# Serializers
# -----------------------------
class PastureGeoSerializer(GeoFeatureModelSerializer):
    # Safe: if Pasture has owner FK, this gives a string; otherwise remove this line + from fields below.
    owner = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = Pasture
        # IMPORTANT: change ONLY if your pasture geometry field isn't named "geometry"
        geo_field = "geometry"
        fields = ("id", "name", "acres", "owner")


class PaddockGeoSerializer(GeoFeatureModelSerializer):
    # Allow POSTing pasture by id
    pasture = serializers.PrimaryKeyRelatedField(queryset=Pasture.objects.all())

    class Meta:
        model = Paddock
        # IMPORTANT: change ONLY if your paddock geometry field isn't named "geometry"
        geo_field = "geometry"
        fields = ("id", "name", "pasture")


# -----------------------------
# ViewSets
# -----------------------------
class PastureGeoViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Router endpoint:
      GET /api/pastures/
      GET /api/pastures/<id>/
    """
    queryset = Pasture.objects.all().order_by("id")
    serializer_class = PastureGeoSerializer
    permission_classes = [IsAuthenticated]


class PaddockGeoViewSet(viewsets.ModelViewSet):
    """
    Router endpoint:
      GET  /api/paddocks/
      POST /api/paddocks/        <-- used by pasture detail draw tool
      GET  /api/paddocks/?pasture=<id>  <-- filter for pasture detail
    """
    queryset = Paddock.objects.select_related("pasture").all().order_by("id")
    serializer_class = PaddockGeoSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ["get", "post", "head", "options"]

    def get_queryset(self):
        qs = super().get_queryset()
        pasture_id = self.request.query_params.get("pasture")
        if pasture_id:
            try:
                qs = qs.filter(pasture_id=int(pasture_id))
            except Exception:
                pass
        return qs

    def create(self, request, *args, **kwargs):
        """
        Accepts JSON:
          {
            "pasture": 4,
            "name": "New Paddock",
            "geometry": { "type": "Polygon|MultiPolygon", "coordinates": [...] }
          }

        Also accepts "pasture_id" instead of "pasture"
        and "boundary" instead of "geometry".
        """
        data = request.data

        pasture_id = data.get("pasture") or data.get("pasture_id")
        name = (data.get("name") or "").strip() or "New Paddock"
        geom_in = data.get("geometry") or data.get("boundary")

        if not pasture_id:
            return Response({"detail": "Missing pasture (or pasture_id)."}, status=status.HTTP_400_BAD_REQUEST)

        if not Pasture.objects.filter(id=pasture_id).exists():
            return Response({"detail": "Pasture not found."}, status=status.HTTP_404_NOT_FOUND)

        try:
            geom = _to_geos_multipolygon(geom_in)
        except Exception as e:
            return Response({"detail": f"Invalid geometry: {e}"}, status=status.HTTP_400_BAD_REQUEST)

        # IMPORTANT:
        # This assumes your Paddock model fields are: pasture (FK), name, geometry (MultiPolygonField).
        # If your field is named "boundary" instead, change geometry=geom to boundary=geom
        paddock = Paddock.objects.create(
            pasture_id=int(pasture_id),
            name=name,
            geometry=geom,
        )

        ser = self.get_serializer(paddock)
        return Response(ser.data, status=status.HTTP_201_CREATED)