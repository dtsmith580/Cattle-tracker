from rest_framework import viewsets
from rest_framework_gis.filters import InBBoxFilter
from django.db.models import F
from cattle_tracker_app.models.pasture_models import Pasture
from cattle_tracker_app.models.paddock_models import Paddock
from .serializers import PastureGeoSerializer, PaddockGeoSerializer

class NoPagination: page_size = None

class PastureGeoViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = PastureGeoSerializer
    pagination_class = NoPagination
    filter_backends = [InBBoxFilter]          # /api/pastures/?in_bbox=minx,miny,maxx,maxy
    bbox_filter_field = "geometry"
    def get_queryset(self):
        return (Pasture.objects
                .select_related("owner")
                .only("id","name","acres","owner","geometry")
                .filter(geometry__isnull=False)
                .annotate(owner_name=F("owner__name")))

class PaddockGeoViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = PaddockGeoSerializer
    pagination_class = NoPagination
    filter_backends = [InBBoxFilter]
    bbox_filter_field = "geometry"
    def get_queryset(self):
        return (Paddock.objects
                .select_related("pasture")
                .only("id","name","pasture","water_source","geometry")
                .filter(geometry__isnull=False))
