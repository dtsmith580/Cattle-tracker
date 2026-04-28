import json
from django.contrib.gis.geos import GEOSGeometry, MultiPolygon
from cattle_tracker_app.models.pasture_models import Pasture
from cattle_tracker_app.models.paddock_models import Paddock

def to_multi(raw):
    if not raw: return None
    s = raw if not isinstance(raw, dict) else json.dumps(raw)
    # Try JSON (GeoJSON Geometry/Feature/FeatureCollection)
    try: obj = json.loads(s) if isinstance(s, (str, bytes)) else None
    except Exception: obj = None
    g = None
    if obj:
        if obj.get("type") == "Feature" and obj.get("geometry"): obj = obj["geometry"]
        if obj.get("type") == "FeatureCollection" and obj.get("features"):
            for feat in obj["features"]:
                geom = feat.get("geometry")
                if geom and geom.get("type") in ("Polygon","MultiPolygon"):
                    obj = geom; break
        if obj.get("type") in ("Polygon","MultiPolygon"): g = GEOSGeometry(json.dumps(obj))
    if g is None:
        try: g = GEOSGeometry(s)  # WKT/EWKT fallback
        except Exception: return None
    if g.srid is None: g.srid = 4326
    if g.geom_type == "Polygon": g = MultiPolygon(g)
    return g if g.geom_type == "MultiPolygon" else None

# Paddocks
upd = 0
for d in Paddock.objects.filter(geometry__isnull=True):
    raw = getattr(d, "boundary", None) or getattr(d, "geometry_json", None)
    g = to_multi(raw)
    if g:
        d.geometry = g
        d.save(update_fields=["geometry"])
        upd += 1
print("Paddocks backfilled:", upd)

# Pastures
upd = 0
for p in Pasture.objects.filter(geometry__isnull=True):
    raw = getattr(p, "boundary", None) or getattr(p, "geometry_json", None)
    g = to_multi(raw)
    if g:
        p.geometry = g
        p.save(update_fields=["geometry"])
        upd += 1
print("Pastures backfilled:", upd)

print("Final counts:",
      "paddocks =", Paddock.objects.exclude(geometry__isnull=True).count(),
      "pastures =", Pasture.objects.exclude(geometry__isnull=True).count())
