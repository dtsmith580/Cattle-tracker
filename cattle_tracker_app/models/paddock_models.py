"""
Paddock model (no Python reprojection) — standardize on EPSG:4326
- Geometry stored as geometry(MultiPolygon, 4326)
- No pyproj/shapely transforms; any area/length calcs should use PostGIS
- Includes a convenience queryset annotation for area in acres (spheroid)

Drop-in reference for: cattle_tracker_app/models/paddock_models.py
(Keep your existing fields; this shows the key parts to remove PROJ/GDAL dependencies.)
"""
from __future__ import annotations

from decimal import Decimal
from typing import Optional

from django.db import models
from django.utils import timezone
from django.contrib.gis.db import models as gis_models
from django.contrib.gis.db.models.functions import Area
from django.contrib.gis.db.models.functions import Cast
from django.db.models import F

# If you reference Pasture
try:
    from cattle_tracker_app.models.pasture_models import Pasture
except Exception:  # pragma: no cover
    Pasture = None  # type: ignore

ACRES_PER_M2 = Decimal("0.000247105381")

class PaddockQuerySet(models.QuerySet):
    def with_area_acres(self):
        """Annotate each row with area_m2 from spheroidal geography, plus area_acres.
        Requires SRID 4326 data. No Python-side PROJ needed.
        """
        qs = self
        if hasattr(self.model, "geometry"):
            qs = qs.annotate(area_m2=Area(Cast(F("geometry"), output_field=gis_models.GeometryField(geom_type="GEOMETRY"),)))
            # On GEOGRAPHY, Area() gives m^2; Cast to GEOGRAPHY via raw expression for portability
            from django.db.models.expressions import RawSQL
            qs = qs.annotate(area_m2=RawSQL("ST_Area(geometry::geography)", ()))
            qs = qs.annotate(area_acres=F("area_m2") * ACRES_PER_M2)
        return qs

class PaddockManager(models.Manager):
    def get_queryset(self):
        return PaddockQuerySet(self.model, using=self._db)

    def with_area_acres(self):
        return self.get_queryset().with_area_acres()


class Paddock(gis_models.Model):
    """Keep your existing fields; ensure geometry is a real MultiPolygon(4326).

    Example fields are shown for context only. Do **not** remove your real fields.
    """
    # --- Your existing fields (examples) ---
    name = models.CharField(max_length=255)
    if Pasture:
        pasture = models.ForeignKey(Pasture, on_delete=models.CASCADE, related_name="paddocks", null=True, blank=True)
    boundary = models.JSONField(null=True, blank=True)  # legacy, optional
    geometry = gis_models.MultiPolygonField(srid=4326, null=True, blank=True)
    water_source = models.CharField(max_length=255, null=True, blank=True)
    acres = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    # Manager with area helpers
    objects = PaddockManager()

    class Meta:
        ordering = ("name", "id")
        indexes = [
            gis_models.Index(fields=["is_active"]),
            models.Index(fields=["name"]),
            # Spatial index should already exist; if not, add via migration:
            # models.Index(name="paddock_geometry_gix", fields=["geometry"], opclasses=["gist_geometry_ops"])
        ]

    def __str__(self) -> str:  # pragma: no cover
        return self.name or f"Paddock #{self.pk}"

    # ---- IMPORTANT: No Python-side reprojection here ----
    # If you previously had code like this:
    #   transformer = Transformer.from_crs(src, 4326, always_xy=True)
    #   geom_proj = shapely.ops.transform(transformer.transform, geom)
    #   ...
    # delete it. Store as 4326 directly, or let PostGIS do any transforms.

    # Optional utility, DB-driven area (no PROJ):
    def area_acres(self) -> Optional[Decimal]:
        if not self.geometry:
            return None
        # Query once to compute spheroidal area via GEOGRAPHY cast
        from django.db import connection
        with connection.cursor() as cur:
            cur.execute("SELECT ST_Area(%s::geography)", [self.geometry.wkt])
            row = cur.fetchone()
        if not row or row[0] is None:
            return None
        return Decimal(row[0]) * ACRES_PER_M2
