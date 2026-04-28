from django.db import models
from django.utils import timezone
from django.contrib import admin
from django.http import JsonResponse
from shapely.geometry import shape
import json
import logging
import builtins as _builtins  # allow safe use of @property decorator
from django.contrib.gis.db import models as gis_models
from django.contrib.gis.geos import GEOSGeometry, MultiPolygon
from django.contrib.gis.geos import GEOSException
from .ownership_models import Owner, OwnerUserAccess

logger = logging.getLogger(__name__)

# ────────────────────────────────────────────────────────────────────────────────
#  Property → Pasture → Paddock (Section)
# ────────────────────────────────────────────────────────────────────────────────

class Property(models.Model):
    name = models.CharField(max_length=100, unique=True)
    location_description = models.CharField(max_length=255, blank=True)
    address = models.CharField(max_length=255, blank=True)
    notes = models.TextField(blank=True)
    owner = models.ForeignKey(Owner, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        app_label = 'cattle_tracker_app'
        db_table = 'cattle_tracker_app_property'
        ordering = ("name",)

    def __str__(self):
        return self.name


class Pasture(models.Model):
    land_property = models.ForeignKey(
        Property,
        on_delete=models.CASCADE,
        related_name="pastures",
        null=True,
        blank=True,
        db_column="property_id",
    )
    name = models.CharField(max_length=100)
    
    # Legacy/geo fields
    location_description = models.CharField(max_length=255, blank=True)
    boundary = models.JSONField(blank=True, null=True)  # legacy boundary
    geometry = gis_models.MultiPolygonField(srid=4326, null=True, blank=True)

    # Size & water
    size_acres = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    total_size_acres = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    number_of_paddocks = models.PositiveIntegerField(null=True, blank=True)
    avg_paddock_size_acres = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    acres = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    water_source_type = models.CharField(
        max_length=100,
        blank=True,
        choices=[
            ('pond', 'Pond'),
            ('well', 'Well'),
            ('creek', 'Creek'),
            ('trough', 'Trough'),
            ('other', 'Other'),
        ],
    )
    water_quantity_gallons = models.PositiveIntegerField(null=True, blank=True)

    # Access/ownership & state
    owner = models.ForeignKey(Owner, on_delete=models.CASCADE, null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(default=timezone.now)

       
    class Meta:
        app_label = 'cattle_tracker_app'
        db_table = 'cattle_tracker_app_pasture'
        ordering = ("name",)
        unique_together = ("land_property", "name")

    def __str__(self):
        return f"{self.land_property.name + ' → ' if self.land_property else ''}{self.name}"

    @_builtins.property
    def total_paddock_acres(self):
        return sum(p.acres for p in self.paddocks.all() if p.acres)
    
    ACRES_PER_M2 = 1 / 4046.8564224
    def save(self, *args, **kwargs):
        
        # Compute acres directly from GEOSGeometry, not JSON
        if self.geometry:
            try:
                g = self.geometry  # GEOSGeometry instance
                # Transform to a projected CRS so .area returns m²
                g_3857 = g.clone()
                g_3857.transform(3857)  # Web Mercator
                area_m2 = g_3857.area
                self.acres = round(area_m2 * self.ACRES_PER_M2, 2)
            except Exception:
                # Leave acres as-is if transform fails
                pass
        super().save(*args, **kwargs)

    def update_acres_and_paddocks(self):
        paddocks = self.paddocks.all()
        total_acres = sum(p.acres for p in paddocks if p.acres)
        count = paddocks.count()
        self.total_size_acres = total_acres or None
        self.number_of_paddocks = count or None
        self.avg_paddock_size_acres = (total_acres / count) if (total_acres and count) else None
        self.save(update_fields=["total_size_acres", "number_of_paddocks", "avg_paddock_size_acres"])


# ────────────────────────────────────────────────────────────────────────────────
# Admin
# ────────────────────────────────────────────────────────────────────────────────


@admin.register(Property)
class PropertyAdmin(admin.ModelAdmin):
    list_display = ("name", "owner", "location_description", "created_at")
    search_fields = ("name", "location_description", "address")


@admin.register(Pasture)
class PastureAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "land_property",
        "total_paddock_acres",
        "size_acres",
        "number_of_paddocks",
        "avg_paddock_size_acres",
        "water_source_type",
        "water_quantity_gallons",
        "is_active",
        "created_at",
    )
    search_fields = ("name", "location_description", "land_property__name")
    list_filter = ("is_active", "water_source_type", "land_property")


# ────────────────────────────────────────────────────────────────────────────────
# GeoJSON view
# ────────────────────────────────────────────────────────────────────────────────

def pasture_geojson_view(request):
    geojson = {"type": "FeatureCollection", "features": []}

    owner_ids = OwnerUserAccess.objects.filter(user=request.user).values_list('owner_id', flat=True)
    accessible_pastures = Pasture.objects.filter(owner_id__in=owner_ids, is_active=True)

    for pasture in accessible_pastures:
        if pasture.boundary:
            boundary = pasture.boundary
            if isinstance(boundary, str):
                try:
                    boundary = json.loads(boundary)
                except json.JSONDecodeError:
                    logger.warning(f"Failed to parse boundary for pasture: {pasture.name}")
                    continue

            if not isinstance(boundary, dict) or 'coordinates' not in boundary:
                logger.warning(f"Invalid boundary format for pasture: {pasture.name}")
                continue

            feature = {
                "type": "Feature",
                "geometry": boundary,
                "properties": {
                    "id": pasture.id,
                    "name": pasture.name,
                    "property": pasture.land_property.name if pasture.land_property else None,
                    "size_acres": float(pasture.acres or 0),
                },
            }
            geojson["features"].append(feature)

    return JsonResponse(geojson)
