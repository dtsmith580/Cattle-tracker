from django.contrib import admin
from cattle_tracker_app.models import Paddock
from django.utils.html import format_html

# --- Mixin to keep admin fast and avoid GDAL/PROJ work on list pages ---
class DeferGeometryAdminMixin:
    """
    Defers heavy geometry fields from the admin changelist queryset.
    - Avoids fetching large geometry payloads
    - Avoids any Python-side reprojection work
    """
    geometry_fields = ("geometry",)               # local geometry to defer
    related_geometry_fields = ("pasture__geometry",)  # defer parent geometry too

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


@admin.register(Paddock)
class PaddockAdmin(DeferGeometryAdminMixin, admin.ModelAdmin):
    list_display = ('pasture_group', 'name', 'acres', 'water_source', 'id')
    list_filter = ('pasture', 'water_source')
    search_fields = ('name', 'pasture__name')
    ordering = ('pasture__name', 'name')
    list_select_related = ('pasture',)  # avoid N+1 on pasture column

    def pasture_group(self, obj):
        return obj.pasture.name
    pasture_group.short_description = 'Pasture'
    pasture_group.admin_order_field = 'pasture__name'

    def colored_water_source(self, obj):
        color_map = {
            'pond': 'blue',
            'creek': 'green',
            'trough': 'sienna',   # a brownish color
            'well': 'gray',
            'none': 'lightgray',
        }
        color = color_map.get(obj.water_source, 'black')
        return format_html('<span style="color: {};">{}</span>', color, obj.get_water_source_display())

    colored_water_source.short_description = 'Water Source'
    colored_water_source.admin_order_field = 'water_source'
