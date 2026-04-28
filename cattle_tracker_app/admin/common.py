# cattle_tracker_app/admin/common.py
from django.contrib import admin

class DeferGeometryAdminMixin:
    """
    Defers heavy geometry fields from admin changelist queries to keep pages fast
    and avoid any GDAL/PROJ work.
    """
    geometry_fields = ("geometry",)           # local geometry fields to defer
    related_geometry_fields = ()              # e.g. ("pasture__geometry",)

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
