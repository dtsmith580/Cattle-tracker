# cattle_tracker_app/api/urls.py

from django.urls import path, include
from rest_framework.routers import DefaultRouter

from cattle_tracker_app.api.pasture_api import PastureGeoViewSet, PaddockGeoViewSet

router = DefaultRouter()
router.register(r"pastures", PastureGeoViewSet, basename="pastures")
router.register(r"paddocks", PaddockGeoViewSet, basename="paddocks")

urlpatterns = [
    # Router endpoints:
    #   /api/pastures/
    #   /api/paddocks/
    path("", include(router.urls)),

    # GeoJSON endpoints backed by DRF viewsets (.geojson suffix)
    path("pastures.geojson", PastureGeoViewSet.as_view({"get": "list"}), name="pastures_geojson"),
    path("paddocks.geojson", PaddockGeoViewSet.as_view({"get": "list"}), name="paddocks_geojson"),
    path("pastures/<int:pk>.geojson", PastureGeoViewSet.as_view({"get": "retrieve"}), name="pasture_detail_geojson"),
    path("paddocks/<int:pk>.geojson", PaddockGeoViewSet.as_view({"get": "retrieve"}), name="paddock_detail_geojson"),
]