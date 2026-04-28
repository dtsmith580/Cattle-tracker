from django.contrib import admin
from cattle_tracker_app.models import Pasture

# --- Mixin to keep admin fast and avoid GDAL/PROJ work on list pages ---
class DeferGeometryAdminMixin:
    """
    Defers heavy geometry fields from the admin changelist queryset.
    - Avoids fetching large geometry payloads
    - Avoids any Python-side reprojection work
    """
    geometry_fields = ("geometry",)      # local geometry to defer
    related_geometry_fields = ()         # e.g. ("owner__geometry",) if you ever add one

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        for f in self.geometry_fields:
            try:
                qs = qs.defer(f)
            except Exception:
                pass
        for rf in getattr(self, "related_geometry_fields", ()):
            try:
                qs = qs.defer(rf)
            except Exception:
                pass
        return qs


@admin.register(Pasture)
class PastureAdmin(DeferGeometryAdminMixin, admin.ModelAdmin):
    # Use a safe owner_name accessor so this doesn't explode if owner is null
    list_display = ("name", "acres", "owner_name", "number_of_paddocks", "id")
    search_fields = ("name", "owner__name")
    list_filter = ("owner",)
    ordering = ("name",)
    list_select_related = ("owner",)  # remove if you don't have an Owner FK

    def owner_name(self, obj):
        owner = getattr(obj, "owner", None)
        return getattr(owner, "name", "—")
    owner_name.short_description = "Owner"
    owner_name.admin_order_field = "owner__name"  # remove if no Owner FK
