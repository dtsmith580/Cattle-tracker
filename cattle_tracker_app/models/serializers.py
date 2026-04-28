from rest_framework_gis.serializers import GeoFeatureModelSerializer
from rest_framework import serializers
from cattle_tracker_app.models.pasture_models import Pasture
from cattle_tracker_app.models.paddock_models import Paddock

class PastureGeoSerializer(GeoFeatureModelSerializer):
    owner = serializers.StringRelatedField(read_only=True)
    class Meta:
        model = Pasture
        geo_field = "geometry"        # SRID=4326
        fields = ("id", "name", "acres", "owner")

class PaddockGeoSerializer(GeoFeatureModelSerializer):
    pasture = serializers.StringRelatedField(read_only=True)
    # Add calculated area field
    area_acres = serializers.SerializerMethodField()

    class Meta:
        model = Paddock
        geo_field = "geometry"
        fields = ("id", "name", "pasture", "water_source", "area_acres")  # add here

    def get_area_acres(self, obj):
        # If your geometry is in SRID 4326 (degrees), you should transform to a projected SRID for accurate area
        # Example for UTM zone 14N (adjust to your location):
        geom = obj.geometry
        if geom.srid != 32614:  # UTM Zone 14N
            geom = geom.transform(32614, clone=True)
        if geom and geom.srid == 32614:
            area_sq_meters = geom.area
            acres = area_sq_meters * 0.000247105
            return round(acres, 2)
        return None
